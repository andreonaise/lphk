package io.github.andreonaise.lphk;

import android.app.*;
import android.text.*;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.io.*;
import java.util.*;

final class ActionBuilder {
    final MainActivity app;
    final EditText editor;
    final ActionForms forms;
    final List<String> lines=new ArrayList<>();
    final ListView list;
    final AlertDialog dialog;
    int selected=-1;
    ActionBuilder(MainActivity app,EditText editor) throws Exception {
        this.app=app; this.editor=editor;
        forms=new ActionForms(new JSONObject(MainActivity.read(app.getAssets().open("forms.json"),1024*1024)));
        if(!editor.getText().toString().isEmpty()) lines.addAll(Arrays.asList(editor.getText().toString().split("\n",-1)));
        LinearLayout body=new LinearLayout(app); body.setOrientation(1); body.setPadding(app.dp(12),0,app.dp(12),0);
        body.addView(app.text("Add actions and arrange them in order. Desktop-only actions can be edited here and exported.",12));
        list=new ListView(app); list.setChoiceMode(ListView.CHOICE_MODE_SINGLE); body.addView(list,new LinearLayout.LayoutParams(-1,app.dp(230)));
        list.setOnItemClickListener((p,v,i,id)->selected=i);
        LinearLayout add=app.row(); body.addView(add);
        app.weighted(add,app.button("Add action…",()->form(-1)));
        app.weighted(add,app.button("Shortcut…",()->shortcut()));
        LinearLayout edit=app.row(); body.addView(edit);
        app.weighted(edit,app.button("Edit",()->{if(selected>=0) form(selected);}));
        app.weighted(edit,app.button("Copy",()->{if(selected>=0) {lines.add(selected+1,lines.get(selected)); selected++; refresh();}}));
        app.weighted(edit,app.button("Remove",()->{if(selected>=0) {lines.remove(selected); selected=Math.min(selected,lines.size()-1); refresh();}}));
        LinearLayout move=app.row(); body.addView(move);
        app.weighted(move,app.button("Move up",()->move(-1))); app.weighted(move,app.button("Move down",()->move(1)));
        ScrollView scroll=new ScrollView(app); scroll.addView(body);
        dialog=new AlertDialog.Builder(app).setTitle("Build actions").setView(scroll).setPositiveButton("Apply to pad editor",null).setNegativeButton("Cancel",null).create();
        dialog.setOnShowListener(d->dialog.getButton(-1).setOnClickListener(v->{try { ActionForms.validateSequence(lines); editor.setText(String.join("\n",lines)); dialog.dismiss(); } catch(Exception e) { app.error(e.getMessage()); }}));
        refresh(); dialog.show();
    }
    void refresh() {
        List<String> labels=new ArrayList<>(); for(int i=0;i<lines.size();i++) labels.add((i+1)+". "+forms.describe(lines.get(i)));
        list.setAdapter(new ArrayAdapter<>(app,android.R.layout.simple_list_item_single_choice,labels)); if(selected>=0) { list.setItemChecked(selected,true); list.setSelection(selected); }
    }
    void move(int direction) { if(selected>=0&&selected+direction>=0&&selected+direction<lines.size()) { Collections.swap(lines,selected,selected+direction); selected+=direction; refresh(); } }
    List<String> choices(String kind) {
        List<String> values=new ArrayList<>();
        if(kind.equals("key")) for(int i=0;i<forms.keys.length();i++) values.add(forms.keys.optString(i));
        else if(kind.equals("page")) for(LayoutData.Page p:app.layout.pages) values.add(p.name);
        else if(kind.equals("label")) for(String line:lines) if(line.trim().startsWith("LABEL ")) values.add(line.trim().substring(6));
        else if(kind.equals("sound")||kind.equals("soundtrack")) { File root=new File(app.getFilesDir(),"user_sounds"); List<File> files=new ArrayList<>(); app.collect(root,files); for(File f:files) values.add(root.toPath().relativize(f.toPath()).toString().replace(File.separatorChar,'/')); }
        return values;
    }
    void form(int index) {
        ActionForms.Parsed parsed=index>=0?forms.parse(lines.get(index)):null;
        if(index>=0&&parsed==null) { app.error("This original line is preserved. Use the text editor to change it, or replace it with a new action."); return; }
        LinearLayout body=new LinearLayout(app); body.setOrientation(1); body.setPadding(app.dp(16),0,app.dp(16),0);
        Spinner selector=new Spinner(app); body.addView(selector);
        List<String> commands=new ArrayList<>(forms.byName.keySet()),names=new ArrayList<>();
        for(String command:commands) names.add(forms.byName.get(command).optString("title"));
        selector.setAdapter(new ArrayAdapter<>(app,android.R.layout.simple_spinner_dropdown_item,names));
        TextView description=app.text("",12); body.addView(description);
        LinearLayout fields=new LinearLayout(app); fields.setOrientation(1); body.addView(fields);
        Map<String,EditText> inputs=new LinkedHashMap<>(); final boolean[] initialized={false};
        selector.setSelection(parsed==null?commands.indexOf("TAP"):commands.indexOf(parsed.command));
        selector.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            public void onNothingSelected(AdapterView<?> parent) {}
            public void onItemSelected(AdapterView<?> parent,View view,int position,long id) {
                try {
                    String command=commands.get(position); JSONObject spec=forms.byName.get(command); fields.removeAllViews(); inputs.clear();
                    boolean restored=!initialized[0]&&parsed!=null&&parsed.command.equals(command); initialized[0]=true;
                    description.setText(spec.optString("description")+"\n"+(ScriptSyntax.localCommand(command)||command.equals("-")?"Runs on Android":"Desktop only — editable and exportable"));
                    JSONArray schema=spec.getJSONArray("fields");
                    for(int i=0;i<schema.length();i++) {
                        JSONObject f=schema.getJSONObject(i); String kind=f.getString("kind");
                        fields.addView(app.text(f.getString("label"),12));
                        AutoCompleteTextView input=new AutoCompleteTextView(app); input.setTextSize(14); input.setSingleLine(true); input.setThreshold(0);
                        if(kind.equals("number")||kind.equals("integer")) input.setInputType(kind.equals("integer")?4098:12290);
                        input.setText(restored?parsed.values.get(f.getString("name")):f.getString("default"));
                        List<String> suggestions=choices(kind); input.setAdapter(new ArrayAdapter<>(app,android.R.layout.simple_dropdown_item_1line,suggestions));
                        input.setOnClickListener(v->{if(!suggestions.isEmpty()) input.showDropDown();}); fields.addView(input); inputs.put(f.getString("name"),input);
                        if(kind.equals("sound")||kind.equals("soundtrack")) fields.addView(app.button("Import audio…",()->{
                            app.pendingScript=null;
                            app.pendingAudioSelection=path->{
                                try {
                                    String chosen=path;
                                    if(kind.equals("sound")&&path.matches(".*\\s.*")) {
                                        File source=app.audioFile(path); chosen="imports/"+UUID.randomUUID()+"-"+source.getName().replaceAll("\\s+","_");
                                        try(InputStream in=new FileInputStream(source);OutputStream out=new FileOutputStream(app.audioFile(chosen))) { MainActivity.copy(in,out,200L*1024*1024); }
                                    }
                                    input.setText(chosen);
                                } catch(Exception e) { app.error(e.getMessage()); }
                            }; app.pick(MainActivity.AUDIO,"audio/*");
                        }));
                    }
                    if(schema.length()==0) fields.addView(app.text("No settings needed.",12));
                } catch(Exception e) { app.error(e.getMessage()); }
            }
        });
        ScrollView scroll=new ScrollView(app); scroll.addView(body);
        AlertDialog settings=new AlertDialog.Builder(app).setTitle("Action settings").setView(scroll).setPositiveButton(index<0?"Add action":"Save settings",null).setNegativeButton("Cancel",null).create();
        settings.setOnShowListener(d->settings.getButton(-1).setOnClickListener(v->{try {
            Map<String,String> values=new LinkedHashMap<>(); for(Map.Entry<String,EditText> entry:inputs.entrySet()) values.put(entry.getKey(),entry.getValue().getText().toString());
            String command=commands.get(selector.getSelectedItemPosition()),line=forms.build(command,values);
            if(index>=0) { lines.set(index,line); selected=index; }
            else { int at=command.startsWith("@")?0:(selected>=0?selected+1:lines.size()); lines.add(at,line); selected=at; }
            refresh(); settings.dismiss();
        } catch(Exception e) { app.error(e.getMessage()); }})); settings.show();
    }
    void shortcut() {
        LinearLayout body=new LinearLayout(app); body.setOrientation(1); body.setPadding(app.dp(16),0,app.dp(16),0);
        body.addView(app.text("Desktop shortcut: hold modifiers, tap a key, release modifiers.",12));
        Map<String,CheckBox> modifiers=new LinkedHashMap<>(); for(String name:Arrays.asList("ctrl","alt","shift","cmd")) { CheckBox box=new CheckBox(app); box.setText(name); box.setChecked(name.equals("ctrl")); body.addView(box); modifiers.put(name,box); }
        AutoCompleteTextView key=new AutoCompleteTextView(app); key.setSingleLine(true); key.setText("c"); key.setThreshold(0); key.setAdapter(new ArrayAdapter<>(app,android.R.layout.simple_dropdown_item_1line,choices("key"))); key.setOnClickListener(v->key.showDropDown()); body.addView(key);
        AlertDialog d=new AlertDialog.Builder(app).setTitle("Keyboard shortcut").setView(body).setPositiveButton("Add shortcut",null).setNegativeButton("Cancel",null).create();
        d.setOnShowListener(v->d.getButton(-1).setOnClickListener(b->{String chosen=key.getText().toString(); if(chosen.isEmpty()||chosen.matches(".*\\s.*")) {app.error("Choose a key; use space for the spacebar.");return;}
            List<String> steps=new ArrayList<>(),held=new ArrayList<>(); for(String name:modifiers.keySet()) if(modifiers.get(name).isChecked()) { steps.add("PRESS "+name); held.add(name); }
            steps.add("TAP "+chosen); Collections.reverse(held); for(String name:held) steps.add("RELEASE "+name);
            int at=selected<0?lines.size():selected+1; lines.addAll(at,steps); selected=at; refresh(); d.dismiss();
        })); d.show();
    }
}
