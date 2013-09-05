The frontend for VAD should not include energy (C0) coefficient since then the VAD would depend on the volume
of the audio and whispered speech would not be detected.

It looks like that the English VAD works well even for Czech.


LOG:

max_files, max_frames_per_segment, trim_segments, n_iter, n_minibatch, lsize, sigmoid
100 50 30 100 200 128 True
N-iter: 99 Mini-batch: 44
Geometric predictive accuracy:  93.99
Mini-batch predictive accuracy: 95.48
Mini-batch sil bias: 61.81
0.00593064279886


max_files, max_frames_per_segment, trim_segments, n_iter, n_minibatch, lsize, sigmoid
1000 50 30 100 200 128 True
N-iter: 99 Mini-batch: 394
Geometric predictive accuracy:  91.63
Mini-batch predictive accuracy: 94.97
Mini-batch sil bias: 78.89
0.00594423718174

max_files, max_frames_per_segment, trim_segments, n_iter, n_minibatch, lsize, sigmoid, fast
1000 50 30 100 200 256 True True
N-iter: 99 Mini-batch: 394
Geometric predictive accuracy:  91.08
Mini-batch predictive accuracy: 93.47
Mini-batch sil bias: 78.89
0.00398181393784

max_files, max_frames_per_segment, trim_segments, n_iter, n_minibatch, lsize, sigmoid, fast
10000 50 30 100 200 256 True True
N-iter: 39 Mini-batch: 231
Geometric predictive accuracy:  89.24
Mini-batch predictive accuracy: 96.98
Mini-batch sil bias: 41.21

max_files, max_frames_per_segment, trim_segments, n_iter, n_minibatch, lsize, sigmoid, fast
10000 100 0 100 200 128 True True
N-iter: 9 Mini-batch: 9960
Geometric predictive accuracy:  86.27
Mini-batch predictive accuracy: 93.97
Mini-batch sil bias: 29.15
0.0150409989838

max_files, max_frames_per_segment, trim_segments, n_iter, n_minibatch, lsize, sigmoid, fast, n_last_frames
10000 50 0 100 200 128 True True 10
N-iter: 15 Mini-batch: 4936
Geometric predictive accuracy:  86.72
Mini-batch predictive accuracy: 69.35
Mini-batch sil bias: 58.29
0.0302727383979

-------------------------

====================================================
0 vs. 10 vs 20 last frames.
====================================================

max_files, max_frames_per_segment, trim_segments, n_iter, n_minibatch, lsize, sigmoid, fast, n_last_frames
100 50 0 100 500 128 True True 0
N-iter: 99 Mini-batch: 56
Geometric predictive accuracy:  88.30
Mini-batch predictive accuracy: 79.76
Mini-batch sil bias: 52.71
0.0235109696268

max_files, max_frames_per_segment, trim_segments, n_iter, n_minibatch, lsize, sigmoid, fast, n_last_frames
100 50 0 100 500 128 True True 10
N-iter: 99 Mini-batch: 56
Geometric predictive accuracy:  88.19
Mini-batch predictive accuracy: 71.74
Mini-batch sil bias: 52.71
0.0213343366988

max_files, max_frames_per_segment, trim_segments, n_iter, n_minibatch, lsize, sigmoid, fast, n_last_frames
100 50 0 100 500 128 True True 20
N-iter: 99 Mini-batch: 56
Geometric predictive accuracy:  88.29
Mini-batch predictive accuracy: 80.96
Mini-batch sil bias: 52.71
0.020856322779

----

max_files, max_frames_per_segment, trim_segments, n_iter, n_minibatch, lsize, sigmoid, fast, n_last_frames
100 50 0 10000 500 128 True True 0
N-iter: 2222 Mini-batch: 32
Geometric predictive accuracy:  99.84
Mini-batch predictive accuracy: 100.00
Mini-batch sil bias: 57.31

max_files, max_frames_per_segment, trim_segments, n_iter, n_minibatch, lsize, sigmoid, fast, n_last_frames
100 50 0 10000 500 128 True True 10
N-iter: 1702 Mini-batch: 5
Geometric predictive accuracy:  99.50
Mini-batch predictive accuracy: 100.00
Mini-batch sil bias: 59.32

max_files, max_frames_per_segment, trim_segments, n_iter, n_minibatch, lsize, sigmoid, fast, n_last_frames
100 50 0 10000 500 128 True True 20
N-iter: 1431 Mini-batch: 44
Geometric predictive accuracy:  99.48
Mini-batch predictive accuracy: 100.00
Mini-batch sil bias: 57.52

====================================================
sigmoid vs. tanh activation of hidden layers
====================================================

tanh appears to significantly worse than sigmoid activation function

max_files, max_frames_per_segment, trim_segments, n_iter, n_minibatch, lsize, sigmoid, fast, n_last_frames
100 50 0 100 500 128 True True 0
N-iter: 17 Mini-batch: 9
Geometric predictive accuracy:  79.63
Mini-batch predictive accuracy: 85.97
Mini-batch sil bias: 62.93
0.0513498365603


max_files, max_frames_per_segment, trim_segments, n_iter, n_minibatch, lsize, sigmoid, fast, n_last_frames
100 50 0 100 500 128 False True 0
N-iter: 12 Mini-batch: 20
Geometric predictive accuracy:  67.90
Mini-batch predictive accuracy: 82.36

====================================================
====================================================
