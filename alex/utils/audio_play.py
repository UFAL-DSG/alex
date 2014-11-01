import pyaudio



def play(cfg, wav):
    # open the audio device
    p = pyaudio.PyAudio()

    chunk = 160
    # open stream
    stream = p.open(format=p.get_format_from_width(pyaudio.paInt32),
                    channels=1,
                    rate=cfg['Audio']['sample_rate'],
                    output=True,
                    frames_per_buffer=chunk)

    wav = various.split_to_bins(wav, chunk)
    for w in wav:
        stream.write(w)

    stream.stop_stream()
    stream.close()
    p.terminate()