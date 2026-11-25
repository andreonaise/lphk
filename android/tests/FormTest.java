package io.github.andreonaise.lphk;

import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import org.json.*;

public class FormTest {
    static int checks;
    static void check(boolean value) { checks++; if(!value) throw new AssertionError("Form check "+checks); }
    public static void main(String[] args) throws Exception {
        ActionForms forms=new ActionForms(new JSONObject(new String(Files.readAllBytes(Paths.get(args[0])),StandardCharsets.UTF_8)));
        JSONArray vectors=new JSONArray(new String(Files.readAllBytes(Paths.get(args[1])),StandardCharsets.UTF_8));
        for(int i=0;i<vectors.length();i++) {
            JSONObject vector=vectors.getJSONObject(i); String command=vector.getString("command");
            JSONObject object=vector.getJSONObject("values"); Map<String,String> values=new LinkedHashMap<>();
            for(String key:object.keySet()) values.put(key,object.getString(key));
            String actual=forms.build(command,values);
            check(actual.equals(vector.getString("script")));
            check(forms.parse(actual)!=null);
            check(forms.build(forms.parse(actual).command,forms.parse(actual).values).equals(actual));
        }
        check(forms.byName.size()==42);
        check(forms.parse("CUSTOM_LEGACY_COMMAND argument")==null);
        check(forms.parse("SOUND_TRACK \"broken")==null);
        ActionForms.validateSequence(Arrays.asList("- comment","@ASYNC","LABEL again","DELAY 1","REPEAT_LABEL again 3"));
        boolean rejected=false;
        try { ActionForms.validateSequence(Arrays.asList("@SIMPLE a","TAP b")); } catch(IllegalArgumentException e) {rejected=true;} check(rejected);
        System.out.println(checks+" Android visual builder checks passed; all command forms match desktop output");
    }
}
