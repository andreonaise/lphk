package io.github.andreonaise.lphk;

import android.app.*;
import android.content.*;
import android.database.Cursor;
import android.graphics.Color;
import android.net.Uri;
import android.os.*;
import android.provider.OpenableColumns;
import android.text.*;
import android.util.AtomicFile;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import java.util.zip.*;

public class MainActivity extends Activity {
    LayoutData layout=new LayoutData();
    AudioEngine audio;
    ScriptEngine scripts;
    MidiConnection midi;
    PadGrid grid;
    WaveformView waveform;
    Spinner pages,tracks;
    TextView status,timer,trackState;
    Button mode;
    EditText skip;
    boolean editing=true,refreshing,fullscreen;
    final Handler handler=new Handler(Looper.getMainLooper());
    final ArrayList<String> trackKeys=new ArrayList<>();
    String trackSignature="";
    EditText pendingScript;
    java.util.function.Consumer<String> pendingAudioSelection;
    boolean busy;
    static final int IMPORT=11,AUDIO=12,EXPORT=13,BUNDLE=14;
    static final int BG=0xff17191b,TEXT=0xffe1e6e9,MUTED=0xff9ca9b1;
    final Runnable ticker=new Runnable() { public void run() {
        if(audio!=null) { audio.tick(); refreshMonitor(); grid.invalidate(); refreshLeds(); }
        handler.postDelayed(this,100);
    }};
    final int[][] lastLeds=new int[9][9];

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        getWindow().setStatusBarColor(BG); getWindow().setNavigationBarColor(BG);
        if(Build.VERSION.SDK_INT>=35) getWindow().getDecorView().setOnApplyWindowInsetsListener((v,insets)->{
            android.graphics.Insets b=insets.getInsets(WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout());
            v.setPadding(b.left,b.top,b.right,b.bottom); return insets;
        });
        try {
            File sounds=new File(getFilesDir(),"user_sounds/examples"); sounds.mkdirs();
            File demo=new File(sounds,"demo_track.wav"); if(!demo.exists()) try(InputStream in=getAssets().open("demo_track.wav");OutputStream out=new FileOutputStream(demo)) { copy(in,out,200*1024*1024); }
            AtomicFile state=new AtomicFile(new File(getFilesDir(),"layout.json"));
            if(state.getBaseFile().exists()) layout=LayoutData.parse(new String(state.readFully(),StandardCharsets.UTF_8));
            else demoLayout();
        } catch(Exception e) { error("Could not restore the layout: "+e.getMessage()); }
        audio=new AudioEngine(this); scripts=new ScriptEngine(this); midi=new MidiConnection(this);
        buildUi(); refresh(); handler.post(ticker);
    }
    int dp(float n) { return Math.round(n*getResources().getDisplayMetrics().density); }
    LinearLayout row() { LinearLayout l=new LinearLayout(this); l.setGravity(Gravity.CENTER_VERTICAL); return l; }
    TextView text(String value,int size) { TextView t=new TextView(this); t.setText(value); t.setTextSize(size); t.setTextColor(TEXT); return t; }
    Button button(String title,Runnable action) {
        Button b=new Button(this); b.setText(title); b.setTextSize(12); b.setAllCaps(false); b.setTextColor(TEXT);
        b.setBackgroundTintList(android.content.res.ColorStateList.valueOf(0xff2b3137));
        b.setOnClickListener(v->{try { action.run(); } catch(Exception e) { error(e.getMessage()); }});
        return b;
    }
    void weighted(LinearLayout row,View child) { row.addView(child,new LinearLayout.LayoutParams(0,dp(48),1)); }
    void buildUi() {
        ScrollView scroll=new ScrollView(this); scroll.setFillViewport(true); scroll.setBackgroundColor(BG);
        LinearLayout body=new LinearLayout(this); body.setOrientation(LinearLayout.VERTICAL); body.setPadding(dp(12),dp(8),dp(12),dp(12)); scroll.addView(body); setContentView(scroll);
        LinearLayout header=row(); body.addView(header); TextView title=text("LPHK",25); header.addView(title,new LinearLayout.LayoutParams(0,dp(50),1));
        header.addView(button("Connect",()->midi.choose())); header.addView(button("Menu",()->menu()));
        LinearLayout pageRow=row(); body.addView(pageRow);
        pageRow.addView(button("‹",()->switchPage((layout.active+layout.pages.size()-1)%layout.pages.size())));
        pages=new Spinner(this); pageRow.addView(pages,new LinearLayout.LayoutParams(0,dp(48),1));
        pages.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() { public void onNothingSelected(AdapterView<?> a) {} public void onItemSelected(AdapterView<?> a,View v,int i,long id) { if(!refreshing&&i!=layout.active) switchPage(i); }});
        pageRow.addView(button("›",()->switchPage((layout.active+1)%layout.pages.size())));
        pageRow.addView(button("+",()->pageName(false)));
        LinearLayout actions=row(); body.addView(actions);
        mode=button("Edit pads",()->{editing=!editing; grid.clearTouches(); updateMode();}); weighted(actions,mode);
        weighted(actions,button("Play / pause all",()->toggleAll())); weighted(actions,button("Stop all",()->{scripts.cancel(); audio.stopAll(-1);}));
        grid=new PadGrid(this); body.addView(grid,new LinearLayout.LayoutParams(-1,-2));
        LinearLayout monitor=row(); body.addView(monitor);
        tracks=new Spinner(this); monitor.addView(tracks,new LinearLayout.LayoutParams(0,dp(45),1));
        tracks.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() { public void onNothingSelected(AdapterView<?> a) {} public void onItemSelected(AdapterView<?> a,View v,int i,long id) { if(!refreshing&&i<trackKeys.size()) audio.selected=trackKeys.get(i); }});
        timer=text("00:00 / 00:00",13); monitor.addView(timer);
        waveform=new WaveformView(this); body.addView(waveform,new LinearLayout.LayoutParams(-1,dp(38)));
        LinearLayout transport=row(); body.addView(transport);
        weighted(transport,button("Play / pause",()->toggleSelected()));
        transport.addView(button("−",()->skip(-1))); transport.addView(button("+",()->skip(1)));
        transport.addView(text("Skip (s)",12)); skip=new EditText(this); skip.setTextSize(13); skip.setSingleLine(true); skip.setInputType(8194);
        skip.setText(getPreferences(0).getString("skip","5")); transport.addView(skip,new LinearLayout.LayoutParams(dp(55),dp(48)));
        skip.addTextChangedListener(new TextWatcher() { public void beforeTextChanged(CharSequence s,int st,int c,int a) {} public void onTextChanged(CharSequence s,int st,int b,int c) { try { ScriptSyntax.number(s.toString(),0.1,3600); getPreferences(0).edit().putString("skip",s.toString()).apply(); } catch(Exception ignored) {} } public void afterTextChanged(Editable e) {} });
        trackState=text("",12); trackState.setTextColor(MUTED); body.addView(trackState);
        status=text("Touchscreen mode · no Launchpad needed",12); status.setPadding(0,dp(12),0,0); body.addView(status);
        updateMode();
    }
    void updateMode() { mode.setText(editing?"Edit pads ✓":"Play pads ✓"); message(editing?"Tap a touchscreen or physical pad to edit its script and colour.":"Tap pads to play. Use Edit pads to change assignments."); }
    void message(String message) { handler.post(()->{if(status!=null) status.setText(message);}); }
    void error(String message) { handler.post(()->{if(!isFinishing()&&!isDestroyed()) { message(message==null?"Operation failed":message); Toast.makeText(this,message==null?"Operation failed":message,Toast.LENGTH_LONG).show(); }}); }
    void refresh() {
        if(pages==null) return; refreshing=true;
        List<String> names=new ArrayList<>(); for(LayoutData.Page p:layout.pages) names.add(p.name);
        pages.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,names)); pages.setSelection(layout.active);
        refreshing=false; trackSignature=""; refreshMonitor(); grid.invalidate(); if(midi!=null) midi.refresh();
    }
    void switchPage(int index) { if(index<0||index>=layout.pages.size()||index==layout.active) return; grid.clearTouches(); scripts.cancel(); layout.active=index; persist(); refresh(); }
    void persist() {
        AtomicFile file=new AtomicFile(new File(getFilesDir(),"layout.json")); FileOutputStream stream=null;
        try { byte[] data=layout.json().toString().getBytes(StandardCharsets.UTF_8); stream=file.startWrite(); stream.write(data); file.finishWrite(stream); }
        catch(Exception e) { if(stream!=null) file.failWrite(stream); error("Could not save: "+e.getMessage()); }
    }
    void demoLayout() {
        layout=new LayoutData();
        LayoutData.Pad p=layout.page().pads[0][1]; p.color=0xff5e9974; p.text="SOUND_TRACK examples/demo_track.wav 80 1500 2000 500";
        p=layout.page().pads[1][1]; p.color=0xff567eaa; p.text="SOUND_TRACK examples/demo_track.wav 50 500 1000 700";
        p=layout.page().pads[3][1]; p.color=0xffa35050; p.text="SOUND_STOP 500";
    }
    String label(String script) {
        try { for(String line:script.split("\\n")) { List<String> w=ScriptSyntax.words(line.trim()); if(w.isEmpty()||w.get(0).startsWith("#")) continue; if(w.get(0).equals("SOUND_TRACK")||w.get(0).equals("SOUND")) return new File(w.get(1)).getName(); return w.get(0); } } catch(Exception ignored) {}
        return "";
    }
    int padColor(int x,int y) {
        AudioEngine.Track t=audio==null?null:audio.tracks.get(layout.key(x,y));
        if(t!=null) { if(t.state.equals("paused")||t.state.equals("pausing")) return 0xffc99b49; if(!t.state.equals("stopped")) return 0xff339660; }
        return layout.page().pads[x][y].color;
    }
    void refreshLeds() {
        if(midi==null||midi.send==null) return;
        for(int x=0;x<9;x++) for(int y=0;y<9;y++) { int c=padColor(x,y); if(c!=lastLeds[x][y]) { lastLeds[x][y]=c; midi.led(x,y,c); } }
    }
    void pad(int x,int y,boolean down) {
        if(!down) { releasePad(x,y); return; }
        if(editing) edit(x,y); else scripts.run(layout.page().pads[x][y].text,layout.key(x,y),layout.page().id);
    }
    void releasePad(int x,int y) { if(scripts!=null) scripts.release(layout.key(x,y)); }
    void edit(int x,int y) {
        LayoutData.Page page=layout.page(); LayoutData.Pad pad=page.pads[x][y];
        LinearLayout body=new LinearLayout(this); body.setOrientation(1); body.setPadding(dp(20),dp(8),dp(20),0);
        TextView note=text("Audio, pages and web commands run here. Desktop keyboard/mouse commands are kept for use on your computer.",12); note.setTextColor(MUTED); body.addView(note);
        EditText script=new EditText(this); script.setText(pad.text); script.setTextSize(13); script.setMinLines(6); script.setGravity(Gravity.TOP); script.setInputType(131073); body.addView(script);
        EditText color=new EditText(this); color.setSingleLine(true); color.setText(String.format(Locale.ROOT,"#%06x",pad.color&0xffffff)); color.setHint("#rrggbb"); body.addView(color);
        LinearLayout swatches=row(); body.addView(swatches);
        int[] colours={0xff599673,0xff537eaa,0xffbd9557,0xffa65757,0xff836ca6,0xff000000};
        for(int c:colours) { Button b=button("",()->color.setText(String.format(Locale.ROOT,"#%06x",c&0xffffff))); b.setBackgroundTintList(android.content.res.ColorStateList.valueOf(c)); weighted(swatches,b); }
        body.addView(button("Build actions…",()->{try {new ActionBuilder(this,script);} catch(Exception e) {error(e.getMessage());}}));
        body.addView(button("Import audio / soundtrack…",()->{pendingAudioSelection=null; pendingScript=script; pick(AUDIO,"audio/*");}));
        body.addView(button("Soundtrack settings…",()->soundtrackSettings(script)));
        body.addView(button("Command guide…",()->guide(script)));
        ScrollView scroll=new ScrollView(this); scroll.addView(body);
        AlertDialog dialog=new AlertDialog.Builder(this).setTitle(page.name+" · pad "+x+","+y).setView(scroll).setPositiveButton("Save",null).setNeutralButton("Unbind",(d,w)->{
            AudioEngine.Track t=audio.tracks.remove(page.id+":"+x+":"+y); if(t!=null) audio.release(t);
            pad.text=""; pad.color=0xff000000; persist(); refresh();
        }).setNegativeButton("Cancel",null).create();
        dialog.setOnShowListener(d->dialog.getButton(-1).setOnClickListener(v->{
            try { int c=Color.parseColor(color.getText().toString()); String value=script.getText().toString();
                for(String line:value.split("\\n")) if(!line.trim().isEmpty()&&!line.trim().startsWith("#")) ScriptSyntax.words(line);
                AudioEngine.Track t=audio.tracks.remove(page.id+":"+x+":"+y); if(t!=null) audio.release(t);
                pad.text=value; pad.color=c; persist(); refresh(); dialog.dismiss();
            } catch(Exception e) { error(e.getMessage()); }
        })); dialog.show();
    }
    void soundtrackSettings(EditText script) {
        List<String> current=new ArrayList<>();
        try { current=ScriptSyntax.words(script.getText().toString().split("\\n")[0]); } catch(Exception ignored) {}
        String[] labels={"Audio path (import a file first)","Volume (0–100)","Play / resume fade-in (seconds)","Stop / end fade-out (seconds)","Pause fade-out (seconds)"};
        String[] values={"examples/demo_track.wav","80","1.5","2","0.5"};
        if(current.size()>1&&current.get(0).equals("SOUND_TRACK")) {
            values[0]=current.get(1); if(current.size()>2) values[1]=current.get(2);
            for(int i=2;i<5;i++) if(current.size()>i+1) try { values[i]=""+(Double.parseDouble(current.get(i+1))/1000); } catch(Exception ignored) {}
        }
        LinearLayout body=new LinearLayout(this); body.setOrientation(1); body.setPadding(dp(20),0,dp(20),0);
        EditText[] fields=new EditText[5];
        for(int i=0;i<5;i++) { body.addView(text(labels[i],12)); fields[i]=new EditText(this); fields[i].setSingleLine(true); fields[i].setText(values[i]); if(i>0) fields[i].setInputType(8194); body.addView(fields[i]); }
        ScrollView scroll=new ScrollView(this); scroll.addView(body);
        AlertDialog d=new AlertDialog.Builder(this).setTitle("Soundtrack").setView(scroll).setPositiveButton("Apply",null).setNegativeButton("Cancel",null).create();
        d.setOnShowListener(v->d.getButton(-1).setOnClickListener(b->{try {
            String path=fields[0].getText().toString(); audioFile(path);
            int vol=(int)ScriptSyntax.number(fields[1].getText().toString(),0,100); int[] fades=new int[3];
            for(int i=0;i<3;i++) fades[i]=(int)Math.round(ScriptSyntax.number(fields[i+2].getText().toString(),0,3600)*1000);
            script.setText("SOUND_TRACK \""+path+"\" "+vol+" "+fades[0]+" "+fades[1]+" "+fades[2]); d.dismiss();
        } catch(Exception e) { error(e.getMessage()); }})); d.show();
    }
    void pageName(boolean rename) {
        EditText name=new EditText(this); name.setSingleLine(true); name.setText(rename?layout.page().name:"Page "+(layout.pages.size()+1));
        AlertDialog d=new AlertDialog.Builder(this).setTitle(rename?"Rename page":"New page").setView(name).setPositiveButton("Save",null).setNegativeButton("Cancel",null).create();
        d.setOnShowListener(v->d.getButton(-1).setOnClickListener(b->{try { String n=name.getText().toString().trim(); layout.uniqueName(n,rename?layout.page():null);
            if(rename) layout.page().name=n; else { layout.pages.add(new LayoutData.Page(n)); switchPage(layout.pages.size()-1); }
            persist(); refresh(); d.dismiss();
        } catch(Exception e) { error(e.getMessage()); }})); d.show();
    }
    void deletePage() {
        if(layout.pages.size()==1) { error("Keep at least one page."); return; }
        new AlertDialog.Builder(this).setMessage("Delete "+layout.page().name+" and stop its tracks?").setPositiveButton("Delete",(d,w)->{
            scripts.cancel(); String prefix=layout.page().id+":";
            Iterator<AudioEngine.Track> iterator=audio.tracks.values().iterator(); while(iterator.hasNext()) { AudioEngine.Track t=iterator.next(); if(t.key.startsWith(prefix)) { audio.release(t); iterator.remove(); } }
            layout.pages.remove(layout.active); layout.active=Math.min(layout.active,layout.pages.size()-1); persist(); refresh();
        }).setNegativeButton("Cancel",null).show();
    }
    void toggleAll() {
        boolean playing=audio.tracks.values().stream().anyMatch(t->!t.state.equals("paused")&&!t.state.equals("stopped")&&!t.state.equals("pausing"));
        if(playing) audio.pauseAll(-1);
        else if(audio.tracks.values().stream().anyMatch(t->t.state.equals("paused")||t.state.equals("pausing"))) audio.resumeAll(-1);
        else for(int x=0;x<9;x++) for(int y=0;y<9;y++) if(layout.page().pads[x][y].text.trim().startsWith("SOUND_TRACK ")) scripts.run(layout.page().pads[x][y].text,layout.key(x,y),layout.page().id);
    }
    void toggleSelected() {
        AudioEngine.Track t=audio.tracks.get(audio.selected);
        if(t!=null) try { audio.toggle(t.key,t.file,Math.round(t.volume*100),t.playFade,t.stopFade,t.pauseFade); } catch(Exception e) { error(e.getMessage()); }
    }
    void skip(int sign) { try { double seconds=ScriptSyntax.number(skip.getText().toString(),.1,3600); audio.seek(audio.selected,sign*seconds,true); } catch(Exception e) { error(e.getMessage()); } }
    String time(int ms) { int seconds=Math.max(0,ms/1000); return String.format(Locale.ROOT,"%02d:%02d",seconds/60,seconds%60); }
    String trackLabel(AudioEngine.Track t) {
        String[] parts=t.key.split(":"); String name="Other page";
        for(LayoutData.Page p:layout.pages) if(p.id.equals(parts[0])) name=p.name;
        return name+" · "+parts[1]+","+parts[2]+" · "+new File(t.file).getName();
    }
    void refreshMonitor() {
        if(tracks==null) return;
        String signature=audio.tracks.keySet().toString()+layout.pages.stream().map(p->p.name).reduce("",(a,b)->a+b);
        if(!signature.equals(trackSignature)) {
            refreshing=true; trackSignature=signature; trackKeys.clear(); trackKeys.addAll(audio.tracks.keySet());
            List<String> labels=new ArrayList<>(); for(AudioEngine.Track t:audio.tracks.values()) labels.add(trackLabel(t));
            if(labels.isEmpty()) labels.add("No soundtracks playing"); tracks.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,labels)); refreshing=false;
        }
        if(!trackKeys.contains(audio.selected)) audio.selected=trackKeys.isEmpty()?null:trackKeys.get(0);
        if(audio.selected!=null) { int index=trackKeys.indexOf(audio.selected); if(tracks.getSelectedItemPosition()!=index) { refreshing=true; tracks.setSelection(index); refreshing=false; } }
        AudioEngine.Track t=audio.tracks.get(audio.selected);
        timer.setText(time(t==null?0:audio.position(t))+" / "+time(t==null?0:t.duration));
        trackState.setText(t==null?"":t.state+" · "+t.file); waveform.invalidate();
    }
    void menu() {
        String[] actions={"Import layout / bundle","Export layout (.lpl)","Export layout + audio (.zip)","Rename page","Delete page","Command guide","Fullscreen","Load demo layout","New blank layout","Disconnect Launchpad","About"};
        new AlertDialog.Builder(this).setTitle("LPHK").setItems(actions,(d,i)->{
            switch(i) {
                case 0: pick(IMPORT,"*/*"); break;
                case 1: create(EXPORT,"application/json","layout.lpl"); break;
                case 2: create(BUNDLE,"application/zip","lphk-layout.zip"); break;
                case 3: pageName(true); break;
                case 4: deletePage(); break;
                case 5: guide(null); break;
                case 6: fullscreen=!fullscreen; if(Build.VERSION.SDK_INT>=30) { WindowInsetsController c=getWindow().getInsetsController(); if(fullscreen) { c.hide(WindowInsets.Type.systemBars()); c.setSystemBarsBehavior(WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE); } else c.show(WindowInsets.Type.systemBars()); } else getWindow().getDecorView().setSystemUiVisibility(fullscreen?5894:0); break;
                case 7: confirmReplace(()->{resetRuntime(); demoLayout(); persist(); refresh();}); break;
                case 8: confirmReplace(()->{resetRuntime(); layout=new LayoutData(); persist(); refresh();}); break;
                case 9: midi.close(); message("Touchscreen mode · Launchpad disconnected"); break;
                case 10: new AlertDialog.Builder(this).setTitle("LPHK Android 0.2.0").setMessage("A standalone touchscreen soundboard and Launchpad Mini layout editor.\n\nScripts run in this app while connected; they are not stored as programs inside the Launchpad. Desktop keyboard/mouse commands remain editable and exportable.\n\nAudio pauses when the app leaves the foreground.\n\nBased on Ella Jameson (nimaid)'s LPHK. GPL-3.0.\nSource: github.com/andreonaise/lphk").setPositiveButton("Close",null).show(); break;
            }
        }).show();
    }
    void guide(EditText editor) {
        try {
            JSONArray entries=new JSONArray(read(getAssets().open("commands.json"),1024*1024));
            LinearLayout body=new LinearLayout(this); body.setOrientation(1); body.setPadding(dp(16),0,dp(16),0);
            EditText search=new EditText(this); search.setHint("Search a command or action"); body.addView(search);
            ListView list=new ListView(this); body.addView(list,new LinearLayout.LayoutParams(-1,dp(330)));
            List<JSONObject> filtered=new ArrayList<>();
            Runnable filter=()->{filtered.clear(); List<String> names=new ArrayList<>(); String q=search.getText().toString().toLowerCase(Locale.ROOT);
                for(int i=0;i<entries.length();i++) { JSONObject e=entries.optJSONObject(i); if(e.toString().toLowerCase(Locale.ROOT).contains(q)) { filtered.add(e); String name=e.optString("name"); names.add(name+" · "+(ScriptSyntax.localCommand(name)?"android":"desktop only")); } }
                list.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_list_item_1,names));
            };
            search.addTextChangedListener(new TextWatcher() { public void beforeTextChanged(CharSequence s,int a,int c,int f) {} public void onTextChanged(CharSequence s,int a,int b,int c) { filter.run(); } public void afterTextChanged(Editable e) {} }); filter.run();
            list.setOnItemClickListener((parent,view,index,id)->{JSONObject e=filtered.get(index); String example=e.optString("example");
                AlertDialog.Builder detail=new AlertDialog.Builder(this).setTitle(e.optString("name")).setMessage(e.optString("syntax")+"\n\n"+e.optString("description")+"\n\n"+(ScriptSyntax.localCommand(e.optString("name"))?"Runs on Android":"Editable here; execution requires desktop LPHK")+"\n\n"+example).setNegativeButton("Close",null).setNeutralButton("Copy",(d,w)->{((android.content.ClipboardManager)getSystemService(CLIPBOARD_SERVICE)).setPrimaryClip(ClipData.newPlainText("LPHK command",example));});
                if(editor!=null) detail.setPositiveButton("Insert",(d,w)->{int at=Math.max(0,editor.getSelectionStart()); editor.getText().insert(at,example+"\n");}); detail.show();
            });
            new AlertDialog.Builder(this).setTitle("Command guide").setView(body).setPositiveButton("Close",null).show();
        } catch(Exception e) { error(e.getMessage()); }
    }
    File audioFile(String relative) throws IOException {
        if(relative.isEmpty()||relative.contains("\"")||relative.contains("\n")||relative.contains("\\")||relative.startsWith("/")||relative.contains(":")) throw new IOException("Use a relative audio path inside user_sounds.");
        File root=new File(getFilesDir(),"user_sounds").getCanonicalFile(),file=new File(root,relative).getCanonicalFile();
        if(!file.getPath().startsWith(root.getPath()+File.separator)) throw new IOException("Audio path escapes user_sounds");
        return file;
    }
    void pick(int code,String type) { startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT).setType(type).addCategory(Intent.CATEGORY_OPENABLE),code); }
    void create(int code,String type,String title) { startActivityForResult(new Intent(Intent.ACTION_CREATE_DOCUMENT).setType(type).putExtra(Intent.EXTRA_TITLE,title).addCategory(Intent.CATEGORY_OPENABLE),code); }
    String fileName(Uri uri) {
        try(Cursor c=getContentResolver().query(uri,new String[]{OpenableColumns.DISPLAY_NAME},null,null,null)) { if(c!=null&&c.moveToFirst()) return c.getString(0); } catch(Exception ignored) {}
        return "track.wav";
    }
    static void copy(InputStream in,OutputStream out,long maximum) throws IOException {
        byte[] b=new byte[65536]; long total=0; int n;
        while((n=in.read(b))!=-1) { total+=n; if(total>maximum) throw new IOException("File is too large"); out.write(b,0,n); }
    }
    static String read(InputStream in,int maximum) throws IOException { try(InputStream stream=in;ByteArrayOutputStream out=new ByteArrayOutputStream()) { copy(stream,out,maximum); return out.toString("UTF-8"); } }
    void background(Runnable operation) { if(busy) { error("Wait for the current import/export to finish."); return; } busy=true; new Thread(()->{try { operation.run(); } finally { handler.post(()->busy=false); }},"LPHK files").start(); }
    @Override protected void onActivityResult(int request,int result,Intent data) {
        super.onActivityResult(request,result,data); if(result!=RESULT_OK||data==null||data.getData()==null) return;
        Uri uri=data.getData();
        if(request==AUDIO) {
            String original=fileName(uri);
            background(()->{File file=null; try {
                String name=original.replaceAll("[^a-zA-Z0-9._ -]","_"); if(name.isEmpty()) name="track.wav";
                String path="imports/"+name; file=audioFile(path); int suffix=2;
                while(file.exists()) { path="imports/"+(suffix++)+"-"+name; file=audioFile(path); }
                file.getParentFile().mkdirs();
                try(InputStream in=getContentResolver().openInputStream(uri);OutputStream out=new FileOutputStream(file)) { copy(in,out,200L*1024*1024); }
                final String sound=path;
                handler.post(()->{if(pendingAudioSelection!=null) {java.util.function.Consumer<String> selection=pendingAudioSelection; pendingAudioSelection=null; selection.accept(sound);} else if(pendingScript!=null) pendingScript.setText("SOUND_TRACK \""+sound+"\" 80 1500 2000 500"); message("Imported "+sound+" · save the pad to keep its binding");});
            } catch(Exception e) { if(file!=null) file.delete(); error(e.getMessage()); } });
        } else if(request==EXPORT||request==BUNDLE) {
            try {
                String json=layout.json().toString(2);
                background(()->{try(OutputStream out=getContentResolver().openOutputStream(uri,"wt")) {
                    if(request==EXPORT) out.write(json.getBytes(StandardCharsets.UTF_8));
                    else try(ZipOutputStream zip=new ZipOutputStream(out)) {
                        zip.putNextEntry(new ZipEntry("layout.lpl")); zip.write(json.getBytes(StandardCharsets.UTF_8)); zip.closeEntry();
                        zipFolder(zip,new File(getFilesDir(),"user_sounds"),"user_sounds/");
                    }
                    message("Export complete");
                } catch(Exception e) { error("Export failed: "+e.getMessage()); } });
            } catch(Exception e) { error(e.getMessage()); }
        } else if(request==IMPORT) confirmReplace(()->background(()->importDocument(uri)));
    }
    void confirmReplace(Runnable action) { new AlertDialog.Builder(this).setTitle("Replace current layout?").setMessage("Export it first if you want to keep a separate copy. Importing stops the current audio.").setPositiveButton("Continue",(d,w)->action.run()).setNegativeButton("Cancel",null).show(); }
    void resetRuntime() { scripts.cancel(); grid.clearTouches(); audio.stopAll(0); for(AudioEngine.Track t:audio.tracks.values()) audio.release(t); audio.tracks.clear(); }
    void zipFolder(ZipOutputStream zip,File directory,String prefix) throws IOException {
        File[] files=directory.listFiles(); if(files==null) return;
        for(File file:files) if(file.isDirectory()) zipFolder(zip,file,prefix+file.getName()+"/"); else {
            zip.putNextEntry(new ZipEntry(prefix+file.getName())); try(InputStream in=new FileInputStream(file)) { copy(in,zip,200L*1024*1024); } zip.closeEntry();
        }
    }
    byte[] digest(File file) throws Exception { MessageDigest hash=MessageDigest.getInstance("SHA-256"); try(InputStream in=new FileInputStream(file)) { byte[] b=new byte[65536]; int n; while((n=in.read(b))!=-1) hash.update(b,0,n); } return hash.digest(); }
    void importDocument(Uri uri) {
        File stage=new File(getCacheDir(),"import-"+UUID.randomUUID()); stage.mkdirs();
        try {
            LayoutData imported;
            try(PushbackInputStream input=new PushbackInputStream(getContentResolver().openInputStream(uri),4)) {
                byte[] header=new byte[4]; int n=input.read(header); if(n>0) input.unread(header,0,n);
                if(n>=2&&header[0]=='P'&&header[1]=='K') {
                    long total=0; int count=0; Set<String> names=new HashSet<>();
                    try(ZipInputStream zip=new ZipInputStream(input)) {
                        ZipEntry e;
                        while((e=zip.getNextEntry())!=null) {
                            if(++count>4096) throw new IOException("Too many files in bundle");
                            String name=e.getName();
                            if(name.contains("\\")||name.startsWith("/")||name.contains(":")||!names.add(name)) throw new IOException("Unsafe bundle path");
                            File target=new File(stage,name).getCanonicalFile();
                            if(!target.getPath().startsWith(stage.getCanonicalPath()+File.separator)) throw new IOException("Bundle path escapes import folder");
                            if(e.isDirectory()) { target.mkdirs(); continue; }
                            if(!name.equals("layout.lpl")&&!name.startsWith("user_sounds/")) throw new IOException("Bundle must contain layout.lpl and user_sounds/");
                            target.getParentFile().mkdirs();
                            try(OutputStream out=new FileOutputStream(target)) { copy(zip,out,Math.min(200L*1024*1024,500L*1024*1024-total)); }
                            total+=target.length();
                        }
                    }
                    imported=LayoutData.parse(read(new FileInputStream(new File(stage,"layout.lpl")),8*1024*1024));
                    List<File> files=new ArrayList<>(); collect(new File(stage,"user_sounds"),files);
                    for(File file:files) {
                        String path=new File(stage,"user_sounds").toPath().relativize(file.toPath()).toString().replace(File.separatorChar,'/'); File target=audioFile(path);
                        if(target.exists()&&!Arrays.equals(digest(file),digest(target))) throw new IOException("An existing sound has different content: "+path+". Rename it in the bundle before importing.");
                    }
                    for(File file:files) {
                        String path=new File(stage,"user_sounds").toPath().relativize(file.toPath()).toString().replace(File.separatorChar,'/'); File target=audioFile(path);
                        if(!target.exists()) { target.getParentFile().mkdirs(); try(InputStream in=new FileInputStream(file);OutputStream out=new FileOutputStream(target)) { copy(in,out,200L*1024*1024); } }
                    }
                } else imported=LayoutData.parse(read(input,8*1024*1024));
            }
            handler.post(()->{resetRuntime(); layout=imported; persist(); refresh(); message("Layout imported · audio files must be present on this phone");});
        } catch(Exception e) { error("Import failed: "+e.getMessage()); }
        finally { removeTemporary(stage); }
    }
    void collect(File directory,List<File> result) { File[] files=directory.listFiles(); if(files!=null) for(File f:files) { if(f.isDirectory()) collect(f,result); else result.add(f); } }
    void removeTemporary(File file) { File[] files=file.listFiles(); if(files!=null) for(File f:files) removeTemporary(f); file.delete(); }
    @Override protected void onStop() { super.onStop(); if(audio!=null) audio.pauseAll(0); if(scripts!=null) scripts.cancel(); if(grid!=null) grid.clearTouches(); }
    @Override protected void onDestroy() { handler.removeCallbacksAndMessages(null); if(scripts!=null) scripts.cancel(); if(midi!=null) midi.destroy(); if(audio!=null) audio.destroy(); super.onDestroy(); }
}
