# libsox-fmt-mp3 must be installed before pysox

## Symptoms 
```
formats: no handler for given file type `mp3'
  File "sox.pyx", line 304, in pysox.sox.CSoxStream.__init__ (pysox/sox.c:3468)
  File "sox.pyx", line 371, in pysox.sox.CSoxStream.open_read (pysox/sox.c:4054)
IOError: No such file
```

