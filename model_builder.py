import pandas as pd
import numpy as np


def get_time_evaluations(jobs_length):
    jobs_length['length'] = (jobs_length.a + 4 * jobs_length.m + jobs_length.b) / 6
    jobs_length['dispersion'] = ((jobs_length.b - jobs_length.a) / 6) ** 2
    jobs_length.drop(['a', 'm', 'b'], inplace=True, axis=1)
    return jobs_length


def get_events(jobs):
    events = []
    for job_set in jobs.sort_values('prev').prev.unique():
        df = jobs[jobs.prev == job_set]
        job_set = job_set.split(',')
        if job_set == ['-']:
            job_set = []
        events.append({'jobs_in': job_set, 'jobs_out': df.job.to_list(), 'jobs_in_copy': job_set})
    return events


def rank_events(events):
    event_rank = 0
    events['len_jobs_in'] = events.jobs_in.apply(lambda x: len(x))
    events['event_rank'] = None
    while events.len_jobs_in.sum() != 0:
        events.len_jobs_in = events.apply(lambda x: len(x.jobs_in), axis=1)
        events.loc[(events['event_rank'].isna()) & (events.len_jobs_in == 0), 'event_rank'] = event_rank
        cross_out = events.loc[events['event_rank'] == event_rank].jobs_out.sum()
        events.jobs_in = events.jobs_in.apply(lambda x: [a for a in x if a not in cross_out])
        event_rank += 1
    x = [x for x in events.jobs_out.sum() if x not in events.jobs_in_copy.sum()]
    events.loc[len(events.index)] = ({'jobs_in': [], 'jobs_out': [], 'jobs_in_copy': x,
                                      'len_jobs_in': 0, 'event_rank': event_rank})
    return events


def build_jobs_table(events):
    jobs = {x: [0, 0] for x in events.jobs_out.sum()}

    def get_job_connections(event):
        for job in event.jobs_out:
            jobs[job][0] = event.name
        for job in event.jobs_in_copy:
            jobs[job][1] = event.name

    events.apply(get_job_connections, axis=1)
    return jobs


def forward_prop_events(jobs, events, _jobs_table):
    time_early = {x: 0 for x in events.index}
    for i in jobs.i.unique():
        for j in jobs[jobs.i == i].j:
            job_time = jobs.loc[(jobs['i'] == i) & (jobs['j'] == j)].length.to_list()[0]
            time_early[j] = max(time_early[j], time_early[i] + job_time)
    return time_early


def backward_prop_events(jobs, time_critical, events):
    time_late = {x: time_critical for x in events.index}
    for i in jobs.i.unique()[::-1]:
        for j in jobs[jobs.i == i].j:
            job_time = jobs.loc[(jobs['i'] == i) & (jobs['j'] == j)].length.to_list()[0]
            time_late[i] = min(time_late[i], time_late[j] - job_time)
    return time_late


def calculate_reserves(jobs, events):
    jobs['full_reserve'] = 0
    jobs['free_reserve'] = 0
    jobs.full_reserve = jobs.apply(lambda x: events.iloc[x.j]['time_late'] - events.iloc[x.i]['time_early'] - x.length,
                                   axis=1)
    jobs.free_reserve = jobs.apply(lambda x: events.iloc[x.j]['time_early'] - events.iloc[x.i]['time_early'] - x.length,
                                   axis=1)
    return jobs


def get_critical_path(events):
    return events[events['event_reserve'] == 0].index.to_list()


def get_model_parameters(jobs, jobs_length):
    events = pd.DataFrame(get_events(jobs))
    events = rank_events(events)
    events = events.drop(['len_jobs_in', 'jobs_in'], axis=1)
    events = events.sort_values('event_rank').reset_index()

    _jobs_table = build_jobs_table(events)
    _df = {'i': [x[0] for x in _jobs_table.values()],
           'j': [x[1] for x in _jobs_table.values()]}
    jobs = pd.DataFrame(_df, index=_jobs_table.keys(), columns={'i', 'j'})
    jobs = jobs.sort_values('i')
    jobs = pd.merge(jobs, jobs_length, how='inner', left_index=True, right_on='job')
    jobs.sort_values('i')

    time_early = forward_prop_events(jobs, events, _jobs_table)
    events['time_early'] = time_early.values()

    time_late = backward_prop_events(jobs, max(events.time_early), events)
    events['time_late'] = time_late.values()

    events['event_reserve'] = events.time_late - events.time_early
    jobs = calculate_reserves(jobs, events)

    critical_path = get_critical_path(events)
    return {'jobs': jobs, 'events': events, 'critical_path': critical_path}


def get_model_coordinates(events, screen_width, screen_height):
    num_columns = events.event_rank.max() + 2
    column_width = screen_width // num_columns

    events_positions = events[['index', 'event_rank']].copy()
    events_positions['x_pos'] = (events_positions.event_rank + 1) * column_width

    res = pd.DataFrame()
    for rank in events_positions.event_rank.unique():
        events_in_rank = events_positions[events_positions.event_rank == rank]
        num_rows = events_in_rank.shape[0] + 1
        row_height = screen_height // num_rows

        events_in_rank.reset_index(drop=True, inplace=True)
        events_in_rank_ = events_in_rank.copy()
        events_in_rank_['y_pos'] = (events_in_rank.index + 1) * row_height
        res = pd.concat([res, events_in_rank_])
    res.reset_index(drop=True, inplace=True)
    return res


def cdf(x):
    x = x / 1.414213562
    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    p = 0.3275911
    s = np.sign(x)
    t = 1 / (1 + s * p * x)
    b = np.exp(-x * x)
    y = (s * s + s) / 2 - s * (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * b / 2
    return y


def get_time_interval_probability(jobs_length, events):
    t_kr = events.time_late.max()
    d_kr = jobs_length.dispersion.sum()
    mse = np.sqrt(d_kr)
    time_intervals = pd.DataFrame()
    time_intervals['start'] = [t_kr * (1 + 0.05 * w) for w in range(0, -11, -1)]
    time_intervals['end'] = [t_kr * (1 + 0.05 * w) for w in range(0, 11)]
    time_intervals['probability'] = (cdf((time_intervals.end - t_kr) / mse) - cdf((time_intervals.start - t_kr) / mse))
    return time_intervals


def get_certain_time_directive(jobs_length, events):
    t_kr = events.time_late.max()
    d_kr = jobs_length.dispersion.sum()
    mse = np.sqrt(d_kr)
    time_directives = pd.DataFrame()
    time_directives['time_directive'] = [t_kr * (1 + 0.1 * w) for w in range(-5, 6)]
    time_directives['probability'] = 0.5 * (1 + cdf((time_directives.time_directive - t_kr) / mse))
    return time_directives
