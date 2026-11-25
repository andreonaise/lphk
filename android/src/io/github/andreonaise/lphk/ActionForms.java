package io.github.andreonaise.lphk;

import org.json.*;
import java.util.*;

/** Uses the same field schema as the desktop builder, including time units. */
final class ActionForms {
    final JSONArray entries,keys;
    final Map<String,JSONObject> byName=new LinkedHashMap<>();
    static final Set<String> REMAINDER=new HashSet<>(Arrays.asList("STRING","CODE","OPEN","@LOAD_LAYOUT","-"));
    ActionForms(JSONObject schema) throws JSONException {
        entries=schema.getJSONArray("commands"); keys=schema.getJSONArray("keys");
        for(int i=0;i<entries.length();i++) { JSONObject e=entries.getJSONObject(i); byName.put(e.getString("command"),e); }
    }
    String numeric(double n) { return n==(long)n?Long.toString((long)n):Double.toString(n); }
    String build(String command,Map<String,String> values) throws JSONException {
        JSONArray fields=byName.get(command).getJSONArray("fields"); List<String> args=new ArrayList<>();
        for(int i=0;i<fields.length();i++) {
            JSONObject f=fields.getJSONObject(i); String kind=f.getString("kind");
            String raw=values.getOrDefault(f.getString("name"),""); if(!kind.equals("remainder")) raw=raw.trim();
            if(raw.contains("\n")||raw.contains("\r")) throw new IllegalArgumentException("Use one line per action.");
            if(raw.isEmpty()) { if(!f.getBoolean("optional")) throw new IllegalArgumentException(f.getString("label")+" is required."); args.add(""); continue; }
            if(kind.equals("number")||kind.equals("integer")) {
                double n=ScriptSyntax.number(raw,f.getDouble("minimum"),f.getDouble("maximum"));
                if(kind.equals("integer")&&n!=(long)n) throw new IllegalArgumentException("Enter a whole number for "+f.getString("label"));
                double scaled=n*f.getDouble("scale");
                if(f.getDouble("scale")==1000) { if(Math.abs(scaled-Math.round(scaled))>0.000001) throw new IllegalArgumentException("Fade times support three decimal places."); scaled=Math.round(scaled); }
                raw=numeric(scaled);
            } else if(!REMAINDER.contains(command)&&!command.equals("PAGE")&&!command.equals("SOUND_TRACK")&&raw.matches(".*\\s.*")) throw new IllegalArgumentException(f.getString("label")+" cannot contain spaces for this command.");
            if((command.equals("PAGE")||command.equals("SOUND_TRACK"))&&(f.getString("name").equals("path")||f.getString("name").equals("page"))) {
                if(raw.contains("\"")) throw new IllegalArgumentException("Names cannot contain a double quote.");
                if(command.equals("SOUND_TRACK")) {
                    raw=raw.replace('\\','/');
                    if(raw.startsWith("/")||raw.contains(":")||Arrays.asList(raw.split("/")).contains("..")||raw.contains("'")) throw new IllegalArgumentException("Use a relative path inside user_sounds without quote characters.");
                    raw="\""+raw+"\"";
                } else if(raw.matches(".*\\s.*")) raw="\""+raw+"\"";
            }
            args.add(raw);
        }
        if((command.equals("SOUND_SKIP")||command.equals("SOUND_SEEK"))&&args.get(1).isEmpty()!=args.get(2).isEmpty()) throw new IllegalArgumentException("Choose both pad coordinates, or leave both blank.");
        while(!args.isEmpty()&&args.get(args.size()-1).isEmpty()) args.remove(args.size()-1);
        Map<String,List<String>> defaults=new HashMap<>();
        defaults.put("TAP",Arrays.asList("space","1","0")); defaults.put("SOUND_TRACK",Arrays.asList("","100","0","0","0"));
        defaults.put("M_LINE",Arrays.asList("0","0","0","0","0","1"));
        defaults.put("M_LINE_MOVE",Arrays.asList("0","0","0","1")); defaults.put("M_LINE_SET",defaults.get("M_LINE_MOVE"));
        defaults.put("M_RECALL_LINE",Arrays.asList("0","1"));
        for(int i=0;i<args.size();i++) if(args.get(i).isEmpty()) args.set(i,defaults.get(command).get(i));
        return command+(args.isEmpty()?"":" "+String.join(" ",args));
    }
    static final class Parsed { String command; Map<String,String> values=new LinkedHashMap<>(); }
    Parsed parse(String line) {
        try {
            String trimmed=line.trim(); if(trimmed.isEmpty()) return null;
            int space=trimmed.indexOf(' '); String command=space<0?trimmed:trimmed.substring(0,space),tail=space<0?"":trimmed.substring(space+1);
            if(trimmed.startsWith("-")) { command="-"; tail=trimmed.substring(1).trim(); }
            if(!byName.containsKey(command)) return null;
            List<String> args;
            if(REMAINDER.contains(command)) args=Arrays.asList(tail);
            else if(command.equals("SOUND_TRACK")) args=ScriptSyntax.words(tail);
            else if(command.equals("PAGE")) args=Arrays.asList(tail.replaceAll("^\"|\"$",""));
            else args=tail.trim().isEmpty()?Collections.emptyList():Arrays.asList(tail.trim().split("\\s+"));
            JSONArray fields=byName.get(command).getJSONArray("fields"); if(args.size()>fields.length()) return null;
            Parsed p=new Parsed(); p.command=command;
            for(int i=0;i<fields.length();i++) {
                JSONObject f=fields.getJSONObject(i); String value=i<args.size()?args.get(i):"";
                if(!value.isEmpty()&&f.getDouble("scale")!=1) value=numeric(Double.parseDouble(value)/f.getDouble("scale"));
                p.values.put(f.getString("name"),value);
            }
            if(command.equals("SOUND_TRACK")) {
                for(String[] setting:new String[][]{{"volume","100"},{"play","0"},{"stop","0"}}) if(p.values.get(setting[0]).isEmpty()) p.values.put(setting[0],setting[1]);
                if(p.values.get("pause").isEmpty()) p.values.put("pause",p.values.get("stop"));
            }
            build(command,p.values); return p;
        } catch(Exception e) { return null; }
    }
    String describe(String line) {
        Parsed p=parse(line);
        if(p==null) return line.trim().isEmpty()?"Blank line":"Original line (kept): "+line;
        List<String> values=new ArrayList<>(); for(String v:p.values.values()) if(!v.isEmpty()) values.add(v);
        return byName.get(p.command).optString("title")+(values.isEmpty()?"":" · "+String.join(", ",values));
    }
    static void validateSequence(List<String> lines) {
        List<String> active=new ArrayList<>(); Set<String> labels=new HashSet<>();
        for(String line:lines) if(!line.trim().isEmpty()&&!line.trim().startsWith("-")&&!line.trim().startsWith("#")) active.add(line.trim());
        for(int i=0;i<active.size();i++) {
            String line=active.get(i);
            if(line.startsWith("@")&&i!=0) throw new IllegalArgumentException("Background / hold-key / load-layout actions must go first.");
            if(line.startsWith("LABEL ")&&!labels.add(line.substring(6))) throw new IllegalArgumentException("Label names must be unique.");
        }
        if(!active.isEmpty()&&(active.get(0).startsWith("@SIMPLE ")||active.get(0).startsWith("@LOAD_LAYOUT "))&&active.size()>1) throw new IllegalArgumentException("Hold-key and load-layout actions each use their own pad.");
        for(String line:active) { String[] words=line.split("\\s+"); if((words[0].endsWith("GOTO_LABEL")||words[0].endsWith("REPEAT_LABEL"))&&words.length>1&&!labels.contains(words[1])) throw new IllegalArgumentException("Add a named point called "+words[1]+" for this jump / repeat."); }
    }
}
