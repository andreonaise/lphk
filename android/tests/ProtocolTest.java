package io.github.andreonaise.lphk;

import java.util.*;

public class ProtocolTest {
    static int checks;
    static void check(boolean value) { checks++; if(!value) throw new AssertionError("Check "+checks); }
    static void rejects(Runnable action) { boolean rejected=false; try { action.run(); } catch(IllegalArgumentException e) { rejected=true; } check(rejected); }
    public static void main(String[] args) {
        List<String> events=new ArrayList<>();
        MidiProtocol p=new MidiProtocol(false,(x,y,down)->events.add(x+","+y+":"+down));
        p.receive(new byte[]{(byte)0x90,0,127},0,3); check(events.get(0).equals("0,1:true"));
        p.receive(new byte[]{0,0},0,2); check(events.get(1).equals("0,1:false"));
        p.receive(new byte[]{(byte)0xb0,104},0,2); p.receive(new byte[]{(byte)0xf8,127},0,2); check(events.get(2).equals("0,0:true"));
        p.receive(new byte[]{(byte)0x80,120,0},0,3); check(events.get(3).equals("8,8:false"));
        p.receive(new byte[]{(byte)0x90,127,127},0,3); check(events.size()==4);
        p.receive(new byte[]{(byte)0xf0,0,32,41,1,2,3,(byte)0xf7},0,8); check(events.size()==4);
        byte[] led=MidiProtocol.led(false,0,1,0xffff0000); check((led[0]&255)==0x90&&led[1]==0&&led[2]==15);
        led=MidiProtocol.led(false,7,0,0xff00ff00); check((led[0]&255)==0xb0&&(led[1]&255)==111&&led[2]==60);
        led=MidiProtocol.led(false,8,8,0xff000000); check((led[1]&255)==120&&led[2]==12);
        check(MidiProtocol.led(false,8,0,0).length==0);
        events.clear(); p=new MidiProtocol(true,(x,y,down)->events.add(x+","+y+":"+down));
        p.receive(new byte[]{(byte)0x90,81,127},0,3); check(events.get(0).equals("0,1:true"));
        p.receive(new byte[]{(byte)0x90,19,0},0,3); check(events.get(1).equals("8,8:false"));
        p.receive(new byte[]{(byte)0xb0,91,127},0,3); check(events.get(2).equals("0,0:true"));
        led=MidiProtocol.led(true,0,1,0xffff8040); check(led.length==13&&led[8]==81&&led[9]==127&&led[10]==64&&led[11]==32);
        check(MidiProtocol.mode(true,true)[7]==1);
        for(boolean mk3:new boolean[]{false,true}) for(int x=0;x<9;x++) for(int y=0;y<9;y++) {
            if(x==8&&y==0) continue;
            final int expectedX=x,expectedY=y;
            MidiProtocol roundtrip=new MidiProtocol(mk3,(a,b,down)->check(a==expectedX&&b==expectedY&&down));
            byte[] packet=MidiProtocol.led(mk3,x,y,0xff00ff00);
            byte[] press=mk3?new byte[]{(byte)(y==0||x==8?0xb0:0x90),packet[8],127}:new byte[]{packet[0],packet[1],127};
            for(byte value:press) roundtrip.receive(new byte[]{value},0,1);
        }
        check(ScriptSyntax.words("SOUND_TRACK \"my song.wav\" 80 0 0").get(1).equals("my song.wav"));
        check(ScriptSyntax.words("PAGE 'Page 2'").get(1).equals("Page 2"));
        rejects(()->ScriptSyntax.words("PAGE \"broken"));
        rejects(()->ScriptSyntax.number("NaN",0,100));
        rejects(()->ScriptSyntax.number("Infinity",0,100));
        rejects(()->ScriptSyntax.validateLocal(ScriptSyntax.words("TAP a")));
        rejects(()->ScriptSyntax.validateLocal(ScriptSyntax.words("SOUND_SKIP 5 9 1")));
        rejects(()->ScriptSyntax.validateLocal(ScriptSyntax.words("SOUND_TRACK a.wav 101")));
        rejects(()->ScriptSyntax.validateLocal(ScriptSyntax.words("SOUND_TRACK a.wav 80 0 0 0 extra")));
        rejects(()->ScriptSyntax.validateLocal(ScriptSyntax.words("WEB javascript:alert(1)")));
        for(String line:Arrays.asList("SOUND_TRACK \"a b.wav\" 80 1500 2000 500","SOUND_SKIP -2.5 0 1","SOUND_SEEK 60","PAGE_NEXT","SOUND_PAUSE 500","REPEAT_LABEL start 3","WAIT_UNPRESSED")) { ScriptSyntax.validateLocal(ScriptSyntax.words(line)); checks++; }
        System.out.println(checks+" Android MIDI / script syntax checks passed");
    }
}
