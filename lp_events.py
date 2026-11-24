import copy, threading, time
import lp_colors

RUN_DELAY = 0.005  # 0.005 == 200 FPS


def unbound_press(x, y):
    print("[lp_events] (" + str(x) + ", " + str(y) + ") Unbound button...")


press_funcs = [[unbound_press for y in range(9)] for x in range(9)]
pressed = [[False for y in range(9)] for x in range(9)]

timer = None
generation = 0


def init(lp_object, epoch=None):
    global timer
    global press_funcs
    timer = threading.Timer(RUN_DELAY, run, (lp_object, generation if epoch is None else epoch))
    timer.daemon = True


def run(lp_object, epoch=None):
    global timer
    epoch = generation if epoch is None else epoch
    if epoch != generation:
        return
    while True:
        if epoch != generation:
            return
        try:
            event = lp_object.ButtonStateXY()
        except Exception as error:
            if epoch == generation:
                print('[lp_events] Device polling stopped:', error)
                stop()
            return
        if epoch != generation:
            return
        if event:
            x = event[0]
            y = event[1]
            try:
                if event[2] == 0:
                    pressed[x][y] = False
                else:
                    pressed[x][y] = True
                    press_funcs[x][y](x, y)
                lp_colors.updateXY(x, y)
            except IndexError:
                pass
        else:
            break
    if epoch == generation:
        init(lp_object, epoch)
        timer.start()


def start(lp_object):
    stop()
    lp_colors.init(lp_object)
    init(lp_object)
    run(lp_object)
    lp_colors.update_all()


def stop():
    global generation, timer
    generation += 1
    if timer is not None:
        timer.cancel()
    timer = None
    for column in pressed:
        for index in range(len(column)):
            column[index] = False


def bind_func_with_colors(x, y, func, off_color):
    global press_funcs
    press_funcs[x][y] = func
    lp_colors.setXY(x, y, off_color)


def unbind(x, y):
    global press_funcs
    press_funcs[x][y] = unbound_press
    lp_colors.setXY(x, y, [0, 0, 0])
    lp_colors.updateXY(x, y)


def unbind_all():
    global press_funcs
    press_funcs = [[unbound_press for y in range(9)] for x in range(9)]
    for x in range(9):
        for y in range(9):
            lp_colors.setXY(x, y, [0, 0, 0])
    lp_colors.raw_clear()
