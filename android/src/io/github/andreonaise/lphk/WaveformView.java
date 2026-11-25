package io.github.andreonaise.lphk;

import android.graphics.*;
import android.view.*;

final class WaveformView extends View {
    final MainActivity app;
    final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
    WaveformView(MainActivity app) { super(app); this.app=app; setContentDescription("Track waveform. Tap to seek."); }
    @Override protected void onDraw(Canvas canvas) {
        AudioEngine.Track t=app.audio.tracks.get(app.audio.selected);
        float fraction=t==null||t.duration==0?0:app.audio.position(t)/(float)t.duration;
        float[] peaks=t==null?new float[0]:t.waveform;
        float maximum=.01f; for(float p:peaks) maximum=Math.max(maximum,p);
        if(peaks.length==0) { paint.setColor(0xff394249); canvas.drawRect(0,getHeight()/2f-2,getWidth(),getHeight()/2f+2,paint); }
        for(int i=0;i<peaks.length;i++) {
            float x=i*getWidth()/(float)peaks.length,amplitude=Math.max(1,peaks[i]/maximum*(getHeight()/2f-3));
            paint.setColor(i/(float)peaks.length<=fraction?(t.state.equals("paused")?0xffc99b49:0xff9fc2ab):0xff394249);
            canvas.drawRect(x,getHeight()/2f-amplitude,x+Math.max(1,getWidth()/(float)peaks.length-1),getHeight()/2f+amplitude,paint);
        }
        paint.setColor(0xffd8e7dc); canvas.drawRect(fraction*getWidth(),0,fraction*getWidth()+2,getHeight(),paint);
    }
    @Override public boolean onTouchEvent(MotionEvent e) {
        if(e.getAction()==MotionEvent.ACTION_DOWN) return true;
        if(e.getAction()==MotionEvent.ACTION_UP) {
            AudioEngine.Track t=app.audio.tracks.get(app.audio.selected);
            if(t!=null) app.audio.seek(t,t.duration/1000.0*Math.max(0,Math.min(1,e.getX()/getWidth())),false);
            performClick(); return true;
        }
        return true;
    }
    @Override public boolean performClick() { super.performClick(); return true; }
}
