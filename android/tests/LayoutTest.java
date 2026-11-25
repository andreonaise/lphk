package io.github.andreonaise.lphk;

import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import org.json.*;

/** Run against JSON-java for portable file interoperability, not Android UI. */
public class LayoutTest {
    static int checks;
    static void check(boolean v) { checks++; if(!v) throw new AssertionError("Layout check "+checks); }
    interface Checked { void run() throws Exception; }
    static void rejects(Checked a) throws Exception { boolean rejected=false; try { a.run(); } catch(JSONException|IllegalArgumentException e) { rejected=true; } check(rejected); }
    public static void main(String[] args) throws Exception {
        LayoutData book=LayoutData.parse(new String(Files.readAllBytes(Paths.get(args[0])),StandardCharsets.UTF_8));
        check(book.pages.size()==2); check(book.page().name.equals("Music"));
        check(book.page().pads[0][1].text.equals("SOUND_TRACK \"imports/my song.wav\" 80 1500 2000 500"));
        check((book.page().pads[0][1].color&0xffffff)==0x559977);
        check(book.resolve("desktop")==0); check(book.resolve("2")==1);
        rejects(()->book.uniqueName("MUSIC",null)); rejects(()->book.uniqueName(" ",null));
        JSONObject serialized=book.json();
        LayoutData reloaded=LayoutData.parse(serialized.toString());
        check(reloaded.page().name.equals("Music")); check(reloaded.pages.get(0).pads[4][4].text.equals("PRESS ctrl\nTAP c\nRELEASE ctrl"));
        JSONObject legacy=new JSONObject().put("version","0.1.0").put("buttons",serialized.get("buttons"));
        check(LayoutData.parse(legacy.toString()).pages.size()==1);
        rejects(()->LayoutData.parse(new JSONObject().put("buttons",new JSONArray()).toString()));
        JSONObject broken=new JSONObject(serialized.toString());
        broken.getJSONArray("pages").getJSONObject(1).put("id",broken.getJSONArray("pages").getJSONObject(0).getString("id"));
        rejects(()->LayoutData.parse(broken.toString()));
        JSONObject badColor=new JSONObject(serialized.toString());
        badColor.getJSONArray("pages").getJSONObject(0).getJSONArray("buttons").getJSONArray(0).getJSONObject(1).put("color",new JSONArray(new int[]{0,256,0}));
        rejects(()->LayoutData.parse(badColor.toString()));
        JSONObject fractional=new JSONObject(serialized.toString());
        fractional.getJSONArray("pages").getJSONObject(0).getJSONArray("buttons").getJSONArray(0).getJSONObject(1).put("color",new JSONArray("[0,1.5,0]"));
        rejects(()->LayoutData.parse(fractional.toString()));
        check(book.pages.size()==2); check(book.page().pads[0][1].color==0xff559977);
        Files.write(Paths.get(args[1]),serialized.toString(2).getBytes(StandardCharsets.UTF_8));
        System.out.println(checks+" desktop/Android layout checks passed");
    }
}
