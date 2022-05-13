import pandas as pd
import model_builder
import graphics_engine

# jobs = pd.read_csv('input/jobs.csv')
jobs = pd.read_csv('input/jobs_repeated.csv')
jobs_length = model_builder.get_time_evaluations(jobs[['job', 'a', 'm', 'b']])
jobs = jobs[['job', 'prev']]

jobs, events, critical_path = model_builder.get_model_parameters(jobs, jobs_length).values()

with open('output/critical_path.txt', 'w') as f:
    f.write('-'.join([str(x) for x in critical_path]))

events_positions = model_builder.get_model_coordinates(events, 1200, 800)
graphics_engine.draw_network(jobs, events, critical_path, events_positions)

time_directives = model_builder.get_certain_time_directive(jobs_length, events)
time_intervals = model_builder.get_time_interval_probability(jobs_length, events)

jobs.to_excel('output/jobs.xlsx', index=False)
events.to_excel('output/events.xlsx', index=False)
time_directives.to_excel('output/time_directives.xlsx', index=False)
time_intervals.to_excel('output/time_intervals.xlsx', index=False)
