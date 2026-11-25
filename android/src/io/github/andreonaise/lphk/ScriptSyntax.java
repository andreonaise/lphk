package io.github.andreonaise.lphk;

import java.util.*;

final class ScriptSyntax {
    static List<String> words(String line) {
        List<String> words=new ArrayList<>(); StringBuilder word=new StringBuilder();
        char quote=0; boolean started=false;
        for(int i=0;i<line.length();i++) {
            char c=line.charAt(i);
            if(quote!=0) { if(c==quote) quote=0; else word.append(c); started=true; }
            else if(c=='"'||c=='\'') { quote=c; started=true; }
            else if(Character.isWhitespace(c)) { if(started) { words.add(word.toString()); word.setLength(0); started=false; } }
            else { word.append(c); started=true; }
        }
        if(quote!=0) throw new IllegalArgumentException("Unclosed quote");
        if(started) words.add(word.toString());
        return words;
    }
    static double number(String value,double minimum,double maximum) {
        double n=Double.parseDouble(value);
        if(!Double.isFinite(n)||n<minimum||n>maximum) throw new IllegalArgumentException("Number must be between "+minimum+" and "+maximum);
        return n;
    }
    static boolean localCommand(String name) {
        return Arrays.asList("SOUND","SOUND_TRACK","SOUND_PAUSE","SOUND_RESUME","SOUND_STOP","SOUND_SKIP","SOUND_SEEK","DELAY","PAGE","PAGE_NEXT","PAGE_PREV","WEB","WEB_NEW","@ASYNC","LABEL","GOTO_LABEL","REPEAT_LABEL","IF_PRESSED_GOTO_LABEL","IF_UNPRESSED_GOTO_LABEL","IF_PRESSED_REPEAT_LABEL","IF_UNPRESSED_REPEAT_LABEL","RESET_REPEATS","WAIT_UNPRESSED").contains(name);
    }
    static void validateLocal(List<String> w) {
        String c=w.get(0); int n=w.size()-1;
        if(!localCommand(c)) throw new IllegalArgumentException(c+" can be edited for desktop LPHK, but cannot run on Android.");
        if(c.equals("SOUND_TRACK")||c.equals("SOUND")) {
            int maximum=c.equals("SOUND")?2:5;
            if(n<1||n>maximum) throw new IllegalArgumentException("Check the arguments for "+c);
            if(n>1) number(w.get(2),0,100);
            for(int i=3;i<w.size();i++) number(w.get(i),0,3600000);
        } else if(c.equals("SOUND_PAUSE")||c.equals("SOUND_RESUME")||c.equals("SOUND_STOP")) {
            if(n>1) throw new IllegalArgumentException("Only one fade time is allowed");
            if(n==1) number(w.get(1),0,3600000);
        } else if(c.equals("SOUND_SKIP")||c.equals("SOUND_SEEK")) {
            if(n!=1&&n!=3) throw new IllegalArgumentException("Use seconds, optionally followed by x y");
            number(w.get(1),c.equals("SOUND_SKIP")?-864000:0,864000);
            if(n==3) for(int i=2;i<=3;i++) { int v=Integer.parseInt(w.get(i)); if(v<0||v>8) throw new IllegalArgumentException("Coordinates must be 0 through 8"); }
        } else if(c.equals("DELAY")) {
            if(n!=1) throw new IllegalArgumentException("DELAY needs seconds"); number(w.get(1),0,86400);
        } else if(c.equals("PAGE")||c.equals("WEB")||c.equals("WEB_NEW")||c.equals("LABEL")||c.endsWith("GOTO_LABEL")) {
            if(n!=1) throw new IllegalArgumentException(c+" needs one argument");
            if((c.equals("WEB")||c.equals("WEB_NEW"))&&!w.get(1).matches("https?://.+")) throw new IllegalArgumentException("Use an http or https URL");
        } else if(c.endsWith("REPEAT_LABEL")) {
            if(n!=2) throw new IllegalArgumentException(c+" needs a label and count"); number(w.get(2),0,1000000);
            Integer.parseInt(w.get(2));
        } else if(n!=0) throw new IllegalArgumentException(c+" does not take arguments");
    }
}
