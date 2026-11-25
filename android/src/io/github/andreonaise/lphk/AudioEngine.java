package io.github.andreonaise.lphk;

import android.media.*;
import android.os.*;
import java.io.*;
import java.util.*;

final class AudioEngine {
    static class Track {
        String key,file,state="loading";
        MediaPlayer player;
        float volume,gain;
        int playFade,stopFade,pauseFade,duration,sequence;
        boolean ready,wantPlay=true;
        float[] waveform=new float[0];
    }
    final MainActivity app;
    final LinkedHashMap<String,Track> tracks=new LinkedHashMap<>();
    final Set<MediaPlayer> effects=new HashSet<>();
    final Handler handler=new Handler(Looper.getMainLooper());
    final AudioManager manager;
    final AudioFocusRequest focus;
    String selected;
    AudioEngine(MainActivity app) {
        this.app=app; manager=(AudioManager)app.getSystemService(MainActivity.AUDIO_SERVICE);
        focus=new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN)
            .setAudioAttributes(new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA).setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build())
            .setOnAudioFocusChangeListener(change->{if(change<0) pauseAll(0);},handler).build();
    }
    boolean focus() {
        if(manager.requestAudioFocus(focus)==AudioManager.AUDIOFOCUS_REQUEST_GRANTED) return true;
        app.error("Another app currently holds audio focus. Try playback again."); return false;
    }
    void toggle(String key,String filename,int volume,int in,int out,int pause) throws IOException {
        Track old=tracks.get(key); selected=key;
        if(old!=null && old.file.equals(filename) && !old.state.equals("stopped")) {
            if(old.state.equals("loading")) { old.wantPlay=!old.wantPlay; return; }
            if(old.state.equals("paused")||old.state.equals("pausing")) resume(old,in); else pause(old,pause);
            return;
        }
        if(tracks.values().stream().filter(t->!t.state.equals("stopped")).count()>=81) throw new IOException("81 soundtrack channels are already in use.");
        File file=app.audioFile(filename);
        if(!file.isFile()) throw new IOException("Audio not found: "+filename+". Import the sound on this phone.");
        if(!focus()) return;
        if(old!=null) release(old);
        Track t=new Track(); t.key=key; t.file=filename; t.volume=volume/100f; t.playFade=in; t.stopFade=out; t.pauseFade=pause;
        MediaPlayer p=new MediaPlayer(); t.player=p;
        p.setAudioAttributes(new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA).setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build());
        try { p.setDataSource(file.getAbsolutePath()); } catch(IOException|RuntimeException e) { p.release(); throw e; }
        tracks.put(key,t);
        p.setOnPreparedListener(player->{
            if(tracks.get(key)!=t || t.player==null) return;
            t.ready=true; t.duration=p.getDuration();
            if(t.wantPlay) { t.state="playing"; t.gain=in>0?0:t.volume; p.setVolume(t.gain,t.gain); p.start(); fade(t,t.volume,in,"playing"); }
            else { t.state="paused"; t.gain=0; }
            app.refresh();
        });
        p.setOnCompletionListener(player->{t.sequence++; t.state="stopped"; t.gain=0; release(t); app.refresh();});
        p.setOnErrorListener((player,what,extra)->{t.state="stopped"; release(t); app.error("Could not decode "+filename+" ("+what+", "+extra+")"); return true;});
        try { p.prepareAsync(); } catch(RuntimeException e) { release(t); tracks.remove(key); throw e; }
        WaveformDecoder.decode(file,peaks->handler.post(()->{if(tracks.get(key)==t) t.waveform=peaks;}));
        app.refresh();
    }
    void release(Track t) { t.sequence++; if(t.player!=null) { t.player.release(); t.player=null; } t.ready=false; }
    int position(Track t) {
        if(t==null) return 0;
        if(t.player==null) return t.state.equals("stopped")?t.duration:0;
        try { return t.ready?t.player.getCurrentPosition():0; } catch(IllegalStateException e) { return 0; }
    }
    void fade(Track t,float target,int duration,String end) {
        int token=++t.sequence; long start=SystemClock.uptimeMillis(); float initial=t.gain;
        handler.post(new Runnable() { public void run() {
            if(token!=t.sequence || t.player==null || !t.ready) return;
            float progress=duration==0?1:Math.min(1,(SystemClock.uptimeMillis()-start)/(float)duration);
            t.gain=initial+(target-initial)*progress;
            try {
                t.player.setVolume(t.gain,t.gain);
                if(progress<1) handler.postDelayed(this,16);
                else if(end.equals("paused")) { t.player.pause(); t.state="paused"; }
                else if(end.equals("stopped")) { t.player.pause(); t.player.seekTo(0); t.state="stopped"; release(t); t.duration=0; }
                else t.state=end;
            } catch(IllegalStateException e) { t.state="stopped"; release(t); }
        }});
    }
    void pause(Track t,int ms) {
        if(t.state.equals("loading")) { t.wantPlay=false; return; }
        if(t.player==null||t.state.equals("paused")||t.state.equals("stopped")) return;
        t.state="pausing"; fade(t,0,ms,"paused");
    }
    void resume(Track t,int ms) {
        if(t.state.equals("loading")) { t.wantPlay=true; return; }
        if(t.player==null||!focus()) return;
        if(t.state.equals("paused")||t.state.equals("pausing")) { t.state="playing"; t.player.start(); fade(t,t.volume,ms,"playing"); }
    }
    void pauseAll(int override) { for(Track t:tracks.values()) pause(t,override<0?t.pauseFade:override); }
    void resumeAll(int override) { for(Track t:tracks.values()) resume(t,override<0?t.playFade:override); }
    void stopAll(int override) {
        for(Track t:tracks.values()) {
            if(!t.ready) { t.state="stopped"; release(t); }
            else if(!t.state.equals("stopped")) { t.state="stopping"; fade(t,0,override<0?t.stopFade:override,"stopped"); }
        }
        for(MediaPlayer p:effects) p.release(); effects.clear();
    }
    void seek(Track t,double seconds,boolean relative) {
        if(t==null||!t.ready||t.player==null||t.state.equals("stopped")) return;
        long pos=(long)(seconds*1000)+(relative?position(t):0);
        int target=(int)Math.max(0,Math.min(t.duration-1,pos));
        if(t.state.equals("ending")) { t.sequence++; t.state="playing"; t.gain=t.volume; t.player.setVolume(t.gain,t.gain); }
        t.player.seekTo(target,MediaPlayer.SEEK_CLOSEST);
    }
    void seek(String key,double seconds,boolean relative) {
        if(key!=null) seek(tracks.get(key),seconds,relative); else for(Track t:tracks.values()) seek(t,seconds,relative);
    }
    void oneShot(String filename,int volume) throws IOException {
        File file=app.audioFile(filename); if(!file.isFile()) throw new IOException("Audio not found: "+filename);
        if(!focus()) return;
        MediaPlayer p=new MediaPlayer();
        try {
            p.setDataSource(file.getAbsolutePath()); effects.add(p);
            p.setOnPreparedListener(player->{p.setVolume(volume/100f,volume/100f); p.start();});
            p.setOnCompletionListener(player->{effects.remove(p); p.release();});
            p.setOnErrorListener((player,what,extra)->{effects.remove(p); p.release(); app.error("Could not decode "+filename); return true;});
            p.prepareAsync();
        } catch(IOException|RuntimeException e) { effects.remove(p); p.release(); throw e; }
    }
    void tick() {
        for(Track t:tracks.values()) if(t.ready && t.state.equals("playing") && t.stopFade>0 && t.duration-position(t)<=t.stopFade) {
            t.state="ending"; fade(t,0,Math.max(1,t.duration-position(t)),"ending");
        }
    }
    void destroy() { handler.removeCallbacksAndMessages(null); for(Track t:tracks.values()) release(t); for(MediaPlayer p:effects) p.release(); effects.clear(); manager.abandonAudioFocusRequest(focus); }
}
