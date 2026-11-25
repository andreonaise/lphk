package io.github.andreonaise.lphk;

import android.content.Intent;
import android.net.Uri;
import android.os.Handler;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

final class ScriptEngine {
    final MainActivity app;
    final Handler handler;
    final Map<String,Thread> jobs=new ConcurrentHashMap<>();
    final Set<String> held=ConcurrentHashMap.newKeySet();
    final AtomicInteger generation=new AtomicInteger();
    ScriptEngine(MainActivity app) { this.app=app; handler=new Handler(app.getMainLooper()); }
    void release(String key) { held.remove(key); }
    void cancel() { generation.incrementAndGet(); held.clear(); for(Thread t:jobs.values()) t.interrupt(); jobs.clear(); }
    void run(String text,String key,String page) {
        held.add(key);
        Thread previous=jobs.get(key);
        if(previous!=null && previous.isAlive()) { previous.interrupt(); return; }
        List<List<String>> lines=new ArrayList<>(); Map<String,Integer> labels=new HashMap<>();
        try {
            for(String line:text.split("\\r?\\n")) {
                line=line.trim(); if(line.isEmpty()||line.startsWith("#")||line.startsWith("-")) continue;
                List<String> words=ScriptSyntax.words(line); ScriptSyntax.validateLocal(words);
                if(words.get(0).equals("LABEL")) labels.put(words.get(1),lines.size());
                lines.add(words);
            }
            for(List<String> w:lines) if(w.get(0).endsWith("GOTO_LABEL")||w.get(0).endsWith("REPEAT_LABEL")) if(!labels.containsKey(w.get(1))) throw new IllegalArgumentException("Unknown label: "+w.get(1));
        } catch(Exception e) { app.error(e.getMessage()); return; }
        final int token=generation.get();
        Thread thread=new Thread(()->{
            Map<Integer,Integer> repeats=new HashMap<>();
            try {
                for(int i=0;i<lines.size();i++) {
                    if(token!=generation.get()||Thread.currentThread().isInterrupted()) break;
                    List<String> w=lines.get(i); String command=w.get(0);
                    if(command.equals("DELAY")) Thread.sleep((long)(Double.parseDouble(w.get(1))*1000));
                    else if(command.equals("WAIT_UNPRESSED")) { while(held.contains(key)) Thread.sleep(10); }
                    else if(command.equals("LABEL")||command.equals("@ASYNC")) {}
                    else if(command.equals("RESET_REPEATS")) repeats.clear();
                    else if(command.endsWith("GOTO_LABEL")||command.endsWith("REPEAT_LABEL")) {
                        boolean condition=command.startsWith("IF_UNPRESSED")?!held.contains(key):!command.startsWith("IF_PRESSED")||held.contains(key);
                        if(command.endsWith("REPEAT_LABEL")) {
                            int done=repeats.getOrDefault(i,0);
                            condition=condition && done<Integer.parseInt(w.get(2));
                            if(condition) repeats.put(i,done+1);
                        }
                        if(condition) i=labels.get(w.get(1));
                        Thread.sleep(1);
                    } else {
                        handler.post(()->{
                            if(token!=generation.get()) return;
                            try { execute(w,key,page); } catch(Exception e) { app.error(e.getMessage()); }
                        });
                        if(command.startsWith("PAGE")) break;
                    }
                }
            } catch(InterruptedException ignored) {}
            finally { jobs.remove(key,Thread.currentThread()); }
        },"LPHK pad");
        jobs.put(key,thread); thread.start();
    }
    int argument(List<String> w,int index,int fallback) { return index<w.size()?(int)Double.parseDouble(w.get(index)):fallback; }
    void execute(List<String> w,String key,String page) throws Exception {
        String c=w.get(0); AudioEngine a=app.audio;
        switch(c) {
            case "SOUND_TRACK": a.toggle(key,w.get(1),argument(w,2,100),argument(w,3,0),argument(w,4,0),argument(w,5,argument(w,4,0))); break;
            case "SOUND": a.oneShot(w.get(1),argument(w,2,100)); break;
            case "SOUND_PAUSE": a.pauseAll(argument(w,1,-1)); break;
            case "SOUND_RESUME": a.resumeAll(argument(w,1,-1)); break;
            case "SOUND_STOP": a.stopAll(argument(w,1,0)); break;
            case "SOUND_SKIP": case "SOUND_SEEK":
                a.seek(w.size()==4?page+":"+w.get(2)+":"+w.get(3):null,Double.parseDouble(w.get(1)),c.equals("SOUND_SKIP")); break;
            case "PAGE": app.switchPage(app.layout.resolve(w.get(1))); break;
            case "PAGE_NEXT": app.switchPage((app.layout.active+1)%app.layout.pages.size()); break;
            case "PAGE_PREV": app.switchPage((app.layout.active+app.layout.pages.size()-1)%app.layout.pages.size()); break;
            case "WEB": case "WEB_NEW": app.startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(w.get(1)))); break;
        }
        app.refresh();
    }
}
