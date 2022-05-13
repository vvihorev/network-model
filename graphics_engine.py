#!/usr/bin/env python
import pygame as pg
import math
import sys
import locale

FPS = 60
fg = 0, 0, 0
# bg = 250, 240, 230
bg = 250, 250, 250
crit = 250, 20, 20

if sys.version_info >= (3,):
    def print_unicode(s):
        e = locale.getpreferredencoding()
        print(s.encode(e, "backslashreplace").decode())
else:
    def print_unicode(s):
        e = locale.getpreferredencoding()
        print(s.encode(e, "backslashreplace"))


def arrow(screen, color, tricolor, start, end, triple_radian):
    pg.draw.line(screen, color, start, end, 2)
    rotation = math.degrees(math.atan2(start[1] - end[1], end[0] - start[0])) + 90
    pg.draw.polygon(screen, tricolor,
                    ((end[0] + math.sin(math.radians(rotation)),
                      end[1] + math.cos(math.radians(rotation))),
                     (end[0] + triple_radian * math.sin(math.radians(rotation - 165)),
                      end[1] + triple_radian * math.cos(math.radians(rotation - 165))),
                     (end[0] + triple_radian * math.sin(math.radians(rotation + 165)),
                      end[1] + triple_radian * math.cos(math.radians(rotation + 165)))))


class NetEventGenerator:
    def __init__(self, surface, radius, width):
        self.surface = surface
        self.radius = radius
        self.width = width

        self.events = {}
        self.event_number = 0

    def add_event(self, center, event_parameters):
        self.events[self.event_number] = NetEvent(center,
                                                  event_parameters,
                                                  self.surface,
                                                  self.radius,
                                                  self.width)
        self.event_number += 1

    def draw_events(self):
        for event in self.events.values():
            event.draw(self.surface)

    def get_in_point(self, event):
        return self.events[event].get_in_point()

    def get_out_point(self, event):
        return self.events[event].get_out_point()


class NetEvent:
    def __init__(self, center, event_parameters, surface, radius, width):
        self.center = center
        self.event_parameters = event_parameters
        self.surface = surface
        self.radius = radius
        self.width = width
        self.rect = pg.draw.circle(self.surface, fg, self.center, self.radius, self.width)

    def get_in_point(self):
        return self.rect.midleft

    def get_out_point(self):
        return self.rect.midright

    def draw(self, screen):
        cc = self.rect.center
        r = self.radius

        font = pg.font.Font(None, 20)
        a_sys_font = pg.font.SysFont("Arial", 13)

        pg.draw.circle(self.surface, fg, cc, r, self.width)
        offset = (r ** 2 / 2) ** (1 / 2)

        diagonal_1_start = (cc[0] - offset, cc[1] - offset)
        diagonal_1_end = (cc[0] + offset, cc[1] + offset)
        diagonal_2_start = (cc[0] - offset, cc[1] + offset)
        diagonal_2_end = (cc[0] + offset, cc[1] - offset)

        pg.draw.line(self.surface, fg, diagonal_1_start, diagonal_1_end, self.width + 1)
        pg.draw.line(self.surface, fg, diagonal_2_start, diagonal_2_end, self.width + 1)

        text = self.event_parameters
        size = font.size(text[0])
        ren = a_sys_font.render(text[0], False, fg, bg)
        screen.blit(ren, (cc[0] - size[0] / 2, cc[1] - r * 2 / 3 - size[1] / 2))

        size = font.size(text[3])
        ren = a_sys_font.render(text[3], False, fg, bg)
        screen.blit(ren, (cc[0] - size[0] / 2, cc[1] + r * 2 / 3 - size[1] / 2))

        size = font.size(text[1])
        ren = a_sys_font.render(text[1], False, fg, bg)
        screen.blit(ren, (cc[0] - r * 2 / 3 - size[0] / 2, cc[1] - size[1] / 2))

        size = font.size(text[2])
        ren = a_sys_font.render(text[2], False, fg, bg)
        screen.blit(ren, (cc[0] + r * 2 / 3 - size[0] / 2, cc[1] - size[1] / 2))


class NetJobGenerator:
    def __init__(self, surface, width, eg):
        self.surface = surface
        self.width = width
        self.eg = eg

        self.jobs = {}
        self.job_number = 1

    def add_job(self, name, length, from_event, to_event, crit):
        self.jobs[self.job_number] = NetJob(
            self.surface,
            self.width,
            name, round(length, 2),
            from_event, to_event,
            crit
        )
        self.job_number += 1

    def draw_jobs(self):
        for job in self.jobs.values():
            job.draw(self.eg)


class NetJob:
    def __init__(self, surface, width, name, length, from_event, to_event, crit):
        self.surface = surface
        self.width = width
        self.name = name
        self.length = length
        self.from_event = from_event
        self.to_event = to_event
        self.crit = crit

    def draw(self, eg):
        from_point = eg.get_out_point(self.from_event)
        to_point = eg.get_in_point(self.to_event)

        color = crit if self.crit else fg
        arrow(self.surface, color, color, from_point, to_point, 14)

        def get_middle(a, b):
            return (a[0] + b[0]) / 2, (a[1] + b[1]) / 2

        cc = get_middle(from_point, to_point)

        font = pg.font.Font(None, 20)
        a_sys_font = pg.font.SysFont("Arial", 15)

        text = '; '.join([str(x) for x in [self.name, self.length]])
        size = font.size(text)
        ren = a_sys_font.render(text, False, fg, bg)
        self.surface.blit(ren, (cc[0] - size[0] / 2, cc[1] - size[1] / 2))


def _create_events(screen, events, ranks_x_locations, events_y_locations):
    eg = NetEventGenerator(screen, 40, 2)
    for i in range(events.shape[0]):
        event = events.iloc[i]
        event_parameters = [round(x, 1) for x in [i, event.time_early, event.time_late, event.event_reserve]]
        event_parameters = [str(x) for x in event_parameters]
        eg.add_event((ranks_x_locations[event.event_rank], events_y_locations[i]), event_parameters)
    return eg


def _create_jobs(screen, jobs, eg, critical_path):
    jg = NetJobGenerator(screen, 2, eg)
    critical_path_jobs = [x for x in zip(critical_path[:-1], critical_path[1:])]
    for i in range(jobs.shape[0]):
        job = jobs.iloc[i]

        crit = (job.i, job.j) in critical_path_jobs

        jg.add_job(job.job, job.length, job.i, job.j, crit)
    return jg


def draw_network(jobs, events, critical_path, events_positions):
    pg.init()
    resolution = 1200, 800
    screen = pg.display.set_mode(resolution)
    screen.fill(bg)

    x_pos = events_positions.sort_values('event_rank').x_pos.unique()
    x_pos = {i: x_pos[i] for i in range(len(x_pos))}
    y_pos = events_positions.y_pos.to_list()
    y_pos = {i: y_pos[i] for i in range(len(y_pos))}
    ranks_x_locations, events_y_locations = x_pos, y_pos

    eg = _create_events(screen, events, ranks_x_locations, events_y_locations)
    jg = _create_jobs(screen, jobs, eg, critical_path)

    rectangles = [[x.rect, False] for x in eg.events.values()]

    clock = pg.time.Clock()
    running = True
    offset_x, offset_y = 0, 0
    while running:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False

            elif event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:
                    for rectangle in rectangles:
                        if rectangle[0].collidepoint(event.pos):
                            rectangle[1] = True
                            mouse_x, mouse_y = event.pos
                            offset_x = rectangle[0].x - mouse_x
                            offset_y = rectangle[0].y - mouse_y

            elif event.type == pg.MOUSEBUTTONUP:
                for rectangle in rectangles:
                    if event.button == 1:
                        rectangle[1] = False

            elif event.type == pg.MOUSEMOTION:
                for rectangle in rectangles:
                    if rectangle[1]:
                        mouse_x, mouse_y = event.pos
                        rectangle[0].x = mouse_x + offset_x
                        rectangle[0].y = mouse_y + offset_y
        screen.fill(bg)

        eg.draw_events()
        jg.draw_jobs()
        pg.display.flip()

        clock.tick(FPS)
    pg.quit()
