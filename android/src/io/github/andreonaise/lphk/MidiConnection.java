package io.github.andreonaise.lphk;

import android.app.AlertDialog;
import android.media.midi.*;
import android.os.Handler;
import java.io.IOException;
import java.util.*;

final class MidiConnection {
    final MainActivity app;
    final MidiManager manager;
    MidiDevice device;
    MidiInputPort send;
    MidiOutputPort receive;
    MidiProtocol protocol;
    boolean opening;
    volatile int generation;
    final Handler handler = new Handler(android.os.Looper.getMainLooper());
    final MidiManager.DeviceCallback callback = new MidiManager.DeviceCallback() {
        @Override public void onDeviceRemoved(MidiDeviceInfo info) {
            if (device!=null && device.getInfo().getId()==info.getId()) { close(); app.message("Launchpad disconnected"); }
        }
    };
    MidiConnection(MainActivity app) {
        this.app=app; manager=(MidiManager)app.getSystemService(MainActivity.MIDI_SERVICE);
        if (manager!=null) manager.registerDeviceCallback(callback,handler);
    }
    void choose() {
        if (manager==null) { app.error("This phone does not provide Android MIDI support."); return; }
        MidiDeviceInfo[] infos=manager.getDevices();
        List<MidiDeviceInfo> available=new ArrayList<>(); List<String> names=new ArrayList<>();
        for (MidiDeviceInfo info:infos) if (info.getInputPortCount()>0 && info.getOutputPortCount()>0) {
            available.add(info); names.add(info.getProperties().getString(MidiDeviceInfo.PROPERTY_NAME,"MIDI device")+" · "+info.getInputPortCount()+" input / "+info.getOutputPortCount()+" output");
        }
        if (available.isEmpty()) { app.error("No MIDI device found. Connect the Launchpad through a USB OTG adapter. A powered hub may be needed."); return; }
        new AlertDialog.Builder(app).setTitle("Connect Launchpad").setItems(names.toArray(new String[0]),(d,i)->choosePorts(available.get(i))).setNegativeButton("Cancel",null).show();
    }
    void choosePorts(MidiDeviceInfo info) {
        List<MidiDeviceInfo.PortInfo> inputs=new ArrayList<>(), outputs=new ArrayList<>();
        for (MidiDeviceInfo.PortInfo p:info.getPorts()) (p.getType()==MidiDeviceInfo.PortInfo.TYPE_INPUT?inputs:outputs).add(p);
        String name=info.getProperties().getString(MidiDeviceInfo.PROPERTY_NAME,"");
        String[] models={"Launchpad Mini / Mini MK2 / classic", "Launchpad Mini MK3"};
        final int[] model={name.toLowerCase(Locale.ROOT).contains("mk3")?1:0};
        new AlertDialog.Builder(app).setTitle("Launchpad model").setSingleChoiceItems(models,model[0],(d,i)->model[0]=i).setPositiveButton("Next",(d,w)->{
            selectPort("Port to send LED colours (choose MIDI, not DAW)",inputs,in->selectPort("Port to receive pad presses",outputs,out->open(info,in,out,model[0]==1)));
        }).setNegativeButton("Cancel",null).show();
    }
    interface PortChoice { void pick(int port); }
    void selectPort(String title,List<MidiDeviceInfo.PortInfo> ports,PortChoice choice) {
        if (ports.size()==1) { choice.pick(ports.get(0).getPortNumber()); return; }
        String[] labels=new String[ports.size()];
        for (int i=0;i<labels.length;i++) labels[i]="Port "+ports.get(i).getPortNumber()+" · "+ports.get(i).getName();
        new AlertDialog.Builder(app).setTitle(title).setItems(labels,(d,i)->choice.pick(ports.get(i).getPortNumber())).setNegativeButton("Cancel",null).show();
    }
    void open(MidiDeviceInfo info,int input,int output,boolean mk3) {
        close(); opening=true; final int token=++generation;
        manager.openDevice(info,opened->{
            if (token!=generation) { if (opened!=null) try { opened.close(); } catch(IOException ignored) {} return; }
            opening=false;
            if (opened==null) { app.error("Android could not open this MIDI device."); return; }
            device=opened; send=device.openInputPort(input); receive=device.openOutputPort(output);
            if (send==null||receive==null) { close(); app.error("The selected MIDI ports are busy or unavailable."); return; }
            protocol=new MidiProtocol(mk3,(x,y,down)->handler.post(()->{if(token==generation) app.pad(x,y,down);}));
            final MidiProtocol parser=protocol;
            receive.connect(new MidiReceiver() {
                @Override public void onSend(byte[] data,int offset,int count,long timestamp) { if(token==generation) parser.receive(data,offset,count); }
            });
            send(MidiProtocol.mode(mk3,true));
            handler.postDelayed(()->{if(token==generation) { refresh(); app.message("Launchpad connected · "+(mk3?"Mini MK3":"Mini / classic")); }},100);
        },handler);
    }
    void send(byte[] message) {
        if (send==null || message.length==0) return;
        try { send.send(message,0,message.length); } catch(IOException e) { close(); app.message("MIDI connection lost: "+e.getMessage()); }
    }
    void refresh() {
        if (protocol==null) return;
        for (int x=0;x<9;x++) for(int y=0;y<9;y++) led(x,y,app.padColor(x,y));
    }
    void led(int x,int y,int color) { if (protocol!=null) send(MidiProtocol.led(protocol.mk3,x,y,color)); }
    void close() {
        generation++; opening=false;
        if (protocol!=null && send!=null) {
            for(int x=0;x<9;x++) for(int y=0;y<9;y++) try { byte[] b=MidiProtocol.led(protocol.mk3,x,y,0); if(b.length>0) send.send(b,0,b.length); } catch(IOException ignored) {}
            try { byte[] b=MidiProtocol.mode(protocol.mk3,false); send.send(b,0,b.length); } catch(IOException ignored) {}
        }
        try { if(receive!=null) receive.close(); } catch(IOException ignored) {}
        try { if(send!=null) send.close(); } catch(IOException ignored) {}
        try { if(device!=null) device.close(); } catch(IOException ignored) {}
        receive=null; send=null; device=null; protocol=null;
    }
    void destroy() { close(); if(manager!=null) manager.unregisterDeviceCallback(callback); }
}
