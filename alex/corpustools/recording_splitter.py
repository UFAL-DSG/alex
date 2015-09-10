from collections import deque
import os
import shutil
import wave
import logging

if __name__ == '__main__':
    import autopath

from alex.components.vad.ffnn import FFNNVADGeneral


LOGGING_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'


default_vad_cfg = {
    'framesize': 512,
    'frameshift': 160,
    'sample_rate': 8000,
    'usehamming': True,
    'preemcoef': 0.97,
    'numchans': 26,
    'ceplifter': 22,
    'numceps': 12,
    'enormalise': True,
    'zmeansource': True,
    'usepower': True,
    'usec0': False,
    'usecmn': False,
    'usedelta': False,
    'useacc': False,
    'n_last_frames': 30, # 15,
    'n_prev_frames': 15,
    'mel_banks_only': True,
    'lofreq': 125,
    'hifreq': 3800,
    'model': 'vad_nnt_1196_hu512_hl1_hla3_pf30_nf15_acf_4.0_mfr32000000_mfl1000000_mfps0_ts0_usec00_usedelta0_useacc0_mbo1_bs1000.tffnn',
    'filter_length': 2,
}

def pdb_on_error():
    import sys

    def info(type, value, tb):
        if hasattr(sys, 'ps1') or not sys.stderr.isatty():
        # we are in interactive mode or we don't have a tty-like
        # device, so we call the default hook
            sys.__excepthook__(type, value, tb)
        else:
            try:
                import ipdb as pdb
            except ImportError:
                import pdb
            import traceback
            # we are NOT in interactive mode, print the exception
            traceback.print_exception(type, value, tb)
            print
            #  then start the debugger in post-mortem mode.
            # pdb.pm() # deprecated
            pdb.post_mortem(tb) # more

    sys.excepthook = info


class RecordingSplitter(object):
    CHANGE_TO_NON_SPEECH = 2
    CHANGE_TO_SPEECH = 1

    speech_thresh = 0.7
    non_speech_thresh = 0.1

    read_buffer_size = 128

    def __init__(self, vad_cfg, speech_thresh=0.7, non_speech_thresh=0.1):
        self.vad_cfg = vad_cfg

        self.speech_thresh = speech_thresh
        self.non_speech_thresh = non_speech_thresh

        logging.info('Loading VAD model.')
        self.vad = FFNNVADGeneral(**vad_cfg)

    def split_single_channel_wav(self, file_name, out_dir, out_prefix):
        logging.info('Splitting %s' % file_name)
        wave_in = wave.open(file_name)

        sample_rate = wave_in.getframerate()
        sample_width = wave_in.getsampwidth()

        bytes_per_second = sample_rate * sample_width

        frames_per_second = bytes_per_second / self.read_buffer_size

        (detection_window_sil,
         detection_window_speech,
         pre_detection_buffer) = self._initialize_buffers(frames_per_second)

        res_files = []
        res_file_cntr = 0

        frames = []

        is_speech = False
        n_read = 0
        n_read_beg = None

        while 1:
            audio_data = wave_in.readframes(self.read_buffer_size)
            n_read += self.read_buffer_size

            if len(audio_data) == 0:
                break

            raw_vad_decision = self.vad.decide(audio_data)
            is_speech, change = self._smoothe_decison(raw_vad_decision, is_speech, detection_window_speech, detection_window_sil)

            if not is_speech:
                pre_detection_buffer.append(audio_data)

            if change == self.CHANGE_TO_SPEECH:
                n_read_beg = n_read - self.read_buffer_size
                frames = []
            elif change == self.CHANGE_TO_NON_SPEECH:
                #if not is_speech and len(frames) > 1:
                self._save_part(res_file_cntr, list(pre_detection_buffer) + frames, out_dir, res_files, wave_in, out_prefix, n_read_beg, n_read, bytes_per_second)
                res_file_cntr += 1
                pre_detection_buffer.extend(frames[-pre_detection_buffer.maxlen:])

            if is_speech:
                frames.append(audio_data)

        if n_read_beg:
            self._save_part(res_file_cntr, frames, out_dir, res_files, wave_in, out_prefix, n_read_beg, n_read, bytes_per_second)

        return res_files

    def _initialize_buffers(self, frames_per_second):
        pre_detection_buffer_frames = int(frames_per_second * 0.5)
        smoothe_decision_window_sil = int(frames_per_second * 0.2)
        smoothe_decision_window_speech = int(frames_per_second * 0.2)

        detection_window_speech = deque(maxlen=smoothe_decision_window_speech)
        detection_window_sil = deque(maxlen=smoothe_decision_window_sil)
        pre_detection_buffer = deque(maxlen=pre_detection_buffer_frames)

        return detection_window_sil, detection_window_speech, pre_detection_buffer


    def _smoothe_decison(self, decision, last_vad, detection_window_speech, detection_window_sil):
        detection_window_speech.append(decision)
        detection_window_sil.append(decision)

        speech = float(sum(detection_window_speech)) / (len(detection_window_speech) + 1.0)
        sil = float(sum(detection_window_sil)) / (len(detection_window_sil) + 1.0)

        vad = last_vad
        change = None
        if last_vad:
            # last decision was speech
            if sil < self.non_speech_thresh:
                vad = False
                change = self.CHANGE_TO_NON_SPEECH
        else:
            if speech > self.speech_thresh:
                vad = True
                change = self.CHANGE_TO_SPEECH

        return vad, change

    def _save_part(self, cntr, frames, out_dir, res_files, wave_in, out_prefix, n_read_beg, n_read_end, bytes_per_second):
        content = b''.join(frames)
        logging.info('Saving part %d (%.1f s).' % (cntr, len(content) * 1.0 / bytes_per_second))

        res_file = os.path.join(out_dir, 'part.%s.%.3d.wav' % (out_prefix, cntr, ))
        wf = wave.open(res_file, 'wb')
        wf.setnchannels(wave_in.getnchannels())
        wf.setsampwidth(wave_in.getsampwidth())
        wf.setframerate(wave_in.getframerate())
        wf.writeframes(content)
        wf.close()

        res_files.append(((n_read_beg * 1.0 / bytes_per_second, n_read_end * 1.0 / bytes_per_second), res_file))


def main(input_dir, pcm_sample_rate, output_dir, ignore_first, ignore_pcm_smaller_than, max_call_log_size,
         min_wav_duration, v, keep_aux_recordings):
    if v:
        logging.basicConfig(level=logging.DEBUG, format=LOGGING_FORMAT)
    else:
        logging.basicConfig(format=LOGGING_FORMAT)

    _mkdir_if_not_exists(output_dir)

    logging.info('Starting.')
    to_process = _find_files_to_split(input_dir, ignore_pcm_smaller_than)

    vad_cfg = default_vad_cfg
    _download_vad_model_if_not_exists(vad_cfg)

    rs = RecordingSplitter(vad_cfg=vad_cfg)

    _split_files(rs, output_dir, to_process, pcm_sample_rate, ignore_first, max_call_log_size, min_wav_duration,
                 keep_aux_recordings)


def _mkdir_if_not_exists(output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)


def _download_vad_model_if_not_exists(vad_cfg):
    if not os.path.exists(vad_cfg['model']):
        os.system('wget "%s"' % (
        'https://vystadial.ms.mff.cuni.cz/download/alex/resources/vad'
        '/voip/%s' %
        vad_cfg['model'], ))


def _find_files_to_split(input_dir, ignore_pcm_smaller_than):
    to_process = []
    logging.info('Searching for files.')
    for root, dirs, files in os.walk(input_dir):
        for file_name in files:
            if file_name.endswith('.pcm'):
                file_size = os.stat(os.path.join(root, file_name))
                if ignore_pcm_smaller_than <= 0 or file_size >= ignore_pcm_smaller_than:
                    to_process.append((file_name, os.path.relpath(root, start=input_dir), root))
    return to_process


def _split_files(rs, output_dir, to_process, pcm_sample_rate, ignore_first, max_call_log_size, min_wav_duration,
                 keep_aux_recordings):
    logging.info('Processing files.')
    for file_name, root, abs_root in to_process:
        file_out_dir = os.path.join(output_dir, root, file_name)

        files = _split_2chan_pcm(rs, abs_root, file_name, file_out_dir, pcm_sample_rate, root, ignore_first)

        bulk_cntr = 0
        while files:
            to_index = max_call_log_size if max_call_log_size > 0 else None
            bulk = files[:to_index]
            files = files[to_index:]
            bulk_out_dir = "%s_%d" % (file_out_dir, bulk_cntr, )

            if not os.path.exists(bulk_out_dir):
                os.makedirs(bulk_out_dir)

            if min_wav_duration > 0.0:
                bulk = _filter_short_wavs(bulk, min_wav_duration)

            for _, wav_path in bulk:
                wav_file_name = os.path.basename(wav_path)
                os.rename(wav_path, os.path.join(bulk_out_dir, wav_file_name))

            _create_session_xml(bulk_out_dir, bulk)

            bulk_cntr += 1

        if not keep_aux_recordings:
            shutil.rmtree(file_out_dir)


def _filter_short_wavs(wavs, min_wav_duration):
    res = []
    for wav_t, wav in wavs:
        fwav = wave.open(wav)
        frames = fwav.getnframes()
        rate = fwav.getframerate()
        duration = frames / float(rate)

        if duration >= min_wav_duration:
            res.append((wav_t, wav))

    return res


def _split_2chan_pcm(rs, abs_root, file_name, out_dir, sample_rate, root, ignore_first):
    file_path = os.path.join(abs_root, file_name)

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    wav_path_a = os.path.join(out_dir, 'all.a.wav')
    wav_path_b = os.path.join(out_dir, 'all.b.wav')
    _convert_to_wav(file_path, sample_rate, wav_path_a, 1, ignore_first)
    _convert_to_wav(file_path, sample_rate, wav_path_b, 2, ignore_first)

    res_files1 = rs.split_single_channel_wav(wav_path_a, out_dir, "a")
    res_files2 = rs.split_single_channel_wav(wav_path_b, out_dir, "b")

    res = res_files1 + res_files2
    res.sort(key=lambda ((tb, te, ), fn, ): tb)

    return res


def _convert_to_wav(in_file, sample_rate, out_file, chan, ignore_first):
    os.system('sox -e signed-integer -b 16 -r %d -c 2 -t raw "%s" "%s" remix %d trim %d' % (sample_rate, in_file, out_file, chan, ignore_first, ))


def _create_session_xml(output_dir, files):
    res = """<?xml version="1.0" encoding="utf-8"?>
<dialogue>
    <config>
    </config>
    <header>
        <host>{host}</host>
        <date>{date}</date>
        <system>{system}</system>
        <version>{version}</version>
        <input_source type="voip"/>
    </header>
    {turns}
</dialogue>
    """

    turn_tpl = """<turn speaker="user" time="{turn_time}" turn_number="{turn_num}">
        <rec starttime="{rec_starttime}" endtime="{rec_endtime}" fname="{rec_filename}" />
        <asr></asr>
        <slu></slu>
    </turn>"""

    res_turns = []
    for i, ((ts, te), fn) in enumerate(files):
        turn = turn_tpl.format(turn_time=ts,
                               turn_num=i + 1,
                               rec_starttime=ts,
                               rec_endtime=te,
                               rec_filename=os.path.basename(fn))
        res_turns.append(turn)

    session_fn = os.path.join(output_dir, 'session.xml')

    with open(session_fn, 'w') as f_out:
        f_out.write(res.format(turns="\n".join(res_turns), host="", date="", system="", version=""))


if __name__ == '__main__':
    pdb_on_error()
    import argparse

    parser = argparse.ArgumentParser()

    parser.usage = ('Recording Splitter takes an input directory with PCM '
                   'recordings and splits them using a voice activity detection'
                   ' mechanism into output dir. It expects the PCM recordings '
                   'to be 2 channel, where each channel contains one side of a'
                   'dialog. The input directory structure is preserved in the '
                   'output directory, where each input file corresponds to an '
                   'output folder of the same name.')
    parser.add_argument('input_dir')
    parser.add_argument('output_dir')
    parser.add_argument('--pcm_sample_rate', type=int, default=8000)
    parser.add_argument('--ignore_first', type=int, default=0)
    parser.add_argument('--ignore_pcm_smaller_than', type=int, default=0)
    parser.add_argument('--max_call_log_size', type=int, default=0)
    parser.add_argument('--min_wav_duration', type=float, default=0.0)
    parser.add_argument('-v', default=False, action='store_true')
    parser.add_argument('--keep_aux_recordings', action='store_true', default=False)

    args = parser.parse_args()

    main(**vars(args))