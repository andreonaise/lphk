package io.github.andreonaise.lphk;

import android.media.*;
import java.io.File;
import java.nio.*;
import java.util.concurrent.*;

final class WaveformDecoder {
    interface Result { void ready(float[] peaks); }
    static final ExecutorService executor=Executors.newSingleThreadExecutor();
    static void decode(File file,Result result) {
        executor.execute(()->{
            MediaExtractor extractor=new MediaExtractor(); MediaCodec codec=null;
            try {
                extractor.setDataSource(file.getAbsolutePath()); MediaFormat format=null;
                for(int i=0;i<extractor.getTrackCount();i++) {
                    MediaFormat f=extractor.getTrackFormat(i);
                    if(f.getString(MediaFormat.KEY_MIME).startsWith("audio/")) { format=f; extractor.selectTrack(i); break; }
                }
                if(format==null) return;
                long duration=format.getLong(MediaFormat.KEY_DURATION);
                int rate=format.getInteger(MediaFormat.KEY_SAMPLE_RATE),channels=format.getInteger(MediaFormat.KEY_CHANNEL_COUNT);
                codec=MediaCodec.createDecoderByType(format.getString(MediaFormat.KEY_MIME));
                codec.configure(format,null,null,0); codec.start();
                boolean inputDone=false,outputDone=false; int encoding=2;
                float[] peaks=new float[256]; MediaCodec.BufferInfo info=new MediaCodec.BufferInfo();
                long deadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(30);
                while(!outputDone && System.nanoTime()<deadline && !Thread.currentThread().isInterrupted()) {
                    if(!inputDone) {
                        int index=codec.dequeueInputBuffer(10000);
                        if(index>=0) {
                            ByteBuffer input=codec.getInputBuffer(index); int size=extractor.readSampleData(input,0);
                            if(size<0) { codec.queueInputBuffer(index,0,0,0,MediaCodec.BUFFER_FLAG_END_OF_STREAM); inputDone=true; }
                            else { codec.queueInputBuffer(index,0,size,extractor.getSampleTime(),0); extractor.advance(); }
                        }
                    }
                    int index=codec.dequeueOutputBuffer(info,10000);
                    if(index==MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                        MediaFormat f=codec.getOutputFormat(); rate=f.getInteger(MediaFormat.KEY_SAMPLE_RATE); channels=f.getInteger(MediaFormat.KEY_CHANNEL_COUNT);
                        encoding=f.containsKey(MediaFormat.KEY_PCM_ENCODING)?f.getInteger(MediaFormat.KEY_PCM_ENCODING):2;
                    } else if(index>=0) {
                        ByteBuffer out=codec.getOutputBuffer(index); out.order(ByteOrder.LITTLE_ENDIAN);
                        if(encoding!=2 && encoding!=4) { codec.releaseOutputBuffer(index,false); return; }
                        int bytes=encoding==4?4:2;
                        int frames=info.size/(bytes*channels);
                        for(int f=0;f<frames;f+=8) {
                            int bin=(int)Math.min(255,Math.max(0,(info.presentationTimeUs+f*1000000L/rate)*256/Math.max(1,duration)));
                            for(int c=0;c<channels;c++) {
                                int at=info.offset+(f*channels+c)*bytes;
                                float v=encoding==4?Math.abs(out.getFloat(at)):Math.abs(out.getShort(at)/32768f);
                                if(Float.isFinite(v)) peaks[bin]=Math.max(peaks[bin],Math.min(1,v));
                            }
                        }
                        outputDone=(info.flags&MediaCodec.BUFFER_FLAG_END_OF_STREAM)!=0;
                        codec.releaseOutputBuffer(index,false);
                    }
                }
                if(outputDone) result.ready(peaks);
            } catch(Exception ignored) { /* Some decoders cannot provide PCM; playback still works. */ }
            finally { if(codec!=null) { try { codec.stop(); } catch(Exception ignored) {} codec.release(); } extractor.release(); }
        });
    }
}
