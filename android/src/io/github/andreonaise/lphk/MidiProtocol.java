package io.github.andreonaise.lphk;

/** Mini/S/classic and Mini MK3 mappings, in the desktop app's x,y coordinates. */
final class MidiProtocol {
    interface Listener { void pad(int x,int y,boolean down); }
    private int status, needed, count;
    private final int[] data = new int[2];
    private boolean sysex;
    boolean mk3;
    private final Listener listener;
    MidiProtocol(boolean mk3, Listener listener) { this.mk3=mk3; this.listener=listener; }
    void receive(byte[] bytes,int offset,int length) {
        for (int i=offset;i<offset+length;i++) {
            int b=bytes[i]&255;
            if (b>=0xf8) continue;
            if (b==0xf0) { sysex=true; status=0; count=0; continue; }
            if (b==0xf7) { sysex=false; continue; }
            if (sysex) continue;
            if ((b&128)!=0) {
                status=b; count=0;
                needed=(b>=0xf0)?(b==0xf2?2:(b==0xf1||b==0xf3?1:0)):((b&0xe0)==0xc0?1:2);
                continue;
            }
            if (status==0 || needed==0) continue;
            data[count++]=b;
            if (count==needed) {
                int kind=status&0xf0;
                if (kind==0x80 || kind==0x90 || kind==0xb0) {
                    int x,y;
                    if (mk3) { x=(data[0]+9)%10; y=(99-data[0])/10; }
                    else if (kind==0xb0) { x=data[0]-104; y=0; }
                    else { x=data[0]&15; y=(data[0]>>4)+1; }
                    if (x>=0 && x<9 && y>=0 && y<9 && !(x==8&&y==0)) listener.pad(x,y,kind!=0x80&&data[1]>0);
                }
                count=0;
                if (status>=0xf0) status=0;
            }
        }
    }
    static byte[] mode(boolean mk3,boolean programmer) {
        return mk3 ? new byte[]{(byte)0xf0,0,32,41,2,13,14,(byte)(programmer?1:0),(byte)0xf7} : new byte[]{(byte)0xb0,0,0};
    }
    static byte[] led(boolean mk3,int x,int y,int color) {
        if (x<0||x>8||y<0||y>8||(x==8&&y==0)) return new byte[0];
        int r=(color>>16)&255,g=(color>>8)&255,b=color&255;
        if (mk3) return new byte[]{(byte)0xf0,0,32,41,2,13,3,3,(byte)(90-10*y+x+1),(byte)(r/2),(byte)(g/2),(byte)(b/2),(byte)0xf7};
        // Classic Mini has red/green LEDs only; approximate blue with green.
        int value=12+Math.min(3,r/64)+16*Math.min(3,Math.max(g,b)/64);
        return new byte[]{(byte)(y==0?0xb0:0x90),(byte)(y==0?104+x:(y-1)*16+x),(byte)value};
    }
}
