package io.github.andreonaise.lphk;

import android.graphics.*;
import android.view.*;
import java.util.*;

final class PadGrid extends View {
    final MainActivity app;
    final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
    final Map<Integer,int[]> pointers=new HashMap<>();
    PadGrid(MainActivity app) { super(app); this.app=app; setContentDescription("Launchpad pads. Switch to edit mode to assign scripts."); }
    @Override protected void onMeasure(int width,int height) {
        int size=Math.min(MeasureSpec.getSize(width),Math.max(app.dp(280),getResources().getDisplayMetrics().heightPixels-app.dp(290)));
        setMeasuredDimension(MeasureSpec.getSize(width),size);
    }
    float cell() { return Math.min(getWidth(),getHeight())/9f; }
    float left() { return (getWidth()-cell()*9)/2; }
    @Override protected void onDraw(Canvas canvas) {
        float cell=cell(),margin=cell*.09f;
        for(int x=0;x<9;x++) for(int y=0;y<9;y++) {
            if(x==8&&y==0) continue;
            RectF r=new RectF(left()+x*cell+margin,y*cell+margin,left()+(x+1)*cell-margin,(y+1)*cell-margin);
            int colour=app.padColor(x,y);
            paint.setColor((colour&0xffffff)==0?0xff272d32:colour); paint.setStyle(Paint.Style.FILL);
            if(x==8||y==0) canvas.drawOval(r,paint); else canvas.drawRoundRect(r,cell*.07f,cell*.07f,paint);
            boolean held=false; for(int[] p:pointers.values()) if(p[0]==x&&p[1]==y) held=true;
            // No text on the small round function buttons.
            if(y>0&&x<8) {
                String text=app.layout.page().pads[x][y].text;
                if(!text.trim().isEmpty()) {
                    String label=app.label(text);
                    paint.setColor(Color.WHITE); paint.setTextSize(Math.min(app.dp(10),cell*.17f)); paint.setTextAlign(Paint.Align.CENTER);
                    while(label.length()>1&&paint.measureText(label)>r.width()-4) label=label.substring(0,label.length()-1);
                    canvas.drawText(label,r.centerX(),r.centerY()+paint.getTextSize()/3,paint);
                }
            }
            if(held) { paint.setColor(0xffd8e7dc); paint.setStyle(Paint.Style.STROKE); paint.setStrokeWidth(app.dp(2)); if(x==8||y==0) canvas.drawOval(r,paint); else canvas.drawRoundRect(r,4,4,paint); paint.setStyle(Paint.Style.FILL); }
        }
    }
    boolean another(int x,int y) { for(int[] p:pointers.values()) if(p[0]==x&&p[1]==y) return true; return false; }
    void clearTouches() { for(int[] p:pointers.values()) app.releasePad(p[0],p[1]); pointers.clear(); invalidate(); }
    @Override public boolean onTouchEvent(MotionEvent event) {
        int action=event.getActionMasked(),index=event.getActionIndex(),id=event.getPointerId(index);
        if(action==MotionEvent.ACTION_DOWN||action==MotionEvent.ACTION_POINTER_DOWN) {
            int x=(int)Math.floor((event.getX(index)-left())/cell()),y=(int)Math.floor(event.getY(index)/cell());
            if(x>=0&&x<9&&y>=0&&y<9&&!(x==8&&y==0)) {
                getParent().requestDisallowInterceptTouchEvent(true);
                boolean existing=another(x,y); pointers.put(id,new int[]{x,y});
                if(!existing) app.pad(x,y,true);
            }
        } else if(action==MotionEvent.ACTION_UP||action==MotionEvent.ACTION_POINTER_UP) {
            int[] pad=pointers.remove(id);
            if(pad!=null&&!another(pad[0],pad[1])) app.releasePad(pad[0],pad[1]);
            if(action==MotionEvent.ACTION_UP) { getParent().requestDisallowInterceptTouchEvent(false); performClick(); }
        } else if(action==MotionEvent.ACTION_CANCEL) clearTouches();
        invalidate(); return true;
    }
    @Override public boolean performClick() { super.performClick(); return true; }
}
