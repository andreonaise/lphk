package io.github.andreonaise.lphk;

import org.json.*;
import java.util.*;

final class LayoutData {
    static final class Pad {
        String text = "";
        int color = 0xff000000;
    }
    static final class Page {
        String id = UUID.randomUUID().toString(), name;
        Pad[][] pads = new Pad[9][9];
        Page(String name) {
            this.name = name;
            for (int x=0;x<9;x++) for (int y=0;y<9;y++) pads[x][y] = new Pad();
        }
    }
    final List<Page> pages = new ArrayList<>();
    int active;
    LayoutData() { pages.add(new Page("Page 1")); }
    Page page() { return pages.get(active); }
    String key(int x, int y) { return page().id + ":" + x + ":" + y; }
    int resolve(String name) {
        for (int i=0;i<pages.size();i++) if (pages.get(i).name.equalsIgnoreCase(name) || pages.get(i).id.equals(name)) return i;
        try { int i = Integer.parseInt(name)-1; if (i>=0 && i<pages.size()) return i; } catch (NumberFormatException ignored) {}
        throw new IllegalArgumentException("No page named " + name);
    }
    void uniqueName(String name, Page except) {
        if (name.trim().isEmpty()) throw new IllegalArgumentException("Choose a page name.");
        for (Page p:pages) if (p!=except && p.name.equalsIgnoreCase(name.trim())) throw new IllegalArgumentException("That page name is already used.");
        if (except==null && pages.size()>=128) throw new IllegalArgumentException("A layout supports up to 128 pages.");
    }
    static LayoutData parse(String text) throws JSONException {
        JSONObject obj = new JSONObject(text);
        LayoutData result = new LayoutData(); result.pages.clear();
        JSONArray pages = obj.optJSONArray("pages");
        if (pages==null || pages.length()==0) pages = new JSONArray().put(new JSONObject().put("id","main").put("name","Page 1").put("buttons",obj.getJSONArray("buttons")));
        if (pages.length()>128) throw new JSONException("Too many pages");
        Set<String> ids = new HashSet<>(), names = new HashSet<>();
        for (int i=0;i<pages.length();i++) {
            JSONObject p = pages.getJSONObject(i);
            Page page = new Page(p.getString("name")); page.id = p.getString("id");
            if (page.name.trim().isEmpty() || page.id.isEmpty() || !ids.add(page.id) || !names.add(page.name.toLowerCase(Locale.ROOT))) throw new JSONException("Invalid or duplicate page");
            JSONArray grid = p.getJSONArray("buttons");
            if (grid.length()!=9) throw new JSONException("A layout needs a 9 by 9 grid");
            for (int x=0;x<9;x++) {
                JSONArray col = grid.getJSONArray(x);
                if (col.length()!=9) throw new JSONException("A layout needs a 9 by 9 grid");
                for (int y=0;y<9;y++) {
                    JSONObject button = col.getJSONObject(y);
                    if (!(button.get("text") instanceof String)) throw new JSONException("Pad script must be text");
                    page.pads[x][y].text = button.getString("text");
                    JSONArray rgb = button.getJSONArray("color");
                    if (rgb.length()!=3) throw new JSONException("Invalid RGB colour");
                    int color = 0xff000000;
                    for (int c=0;c<3;c++) {
                        Object value = rgb.get(c);
                        if (!(value instanceof Integer) || (int)value<0 || (int)value>255) throw new JSONException("Invalid RGB colour");
                        color |= (int)value << (16-c*8);
                    }
                    page.pads[x][y].color = color;
                }
            }
            result.pages.add(page);
            if (page.id.equals(obj.optString("active_page_id"))) result.active = i;
        }
        return result;
    }
    JSONObject json() throws JSONException {
        JSONArray list = new JSONArray();
        for (Page p:pages) {
            JSONArray grid = new JSONArray();
            for (int x=0;x<9;x++) {
                JSONArray col = new JSONArray();
                for (int y=0;y<9;y++) {
                    Pad pad=p.pads[x][y]; int c=pad.color;
                    col.put(new JSONObject().put("text",pad.text).put("color",new JSONArray(new int[]{(c>>16)&255,(c>>8)&255,c&255})));
                }
                grid.put(col);
            }
            list.put(new JSONObject().put("id",p.id).put("name",p.name).put("buttons",grid));
        }
        return new JSONObject().put("version","0.2.0").put("pages",list).put("active_page_id",page().id).put("buttons",list.getJSONObject(active).getJSONArray("buttons"));
    }
}
