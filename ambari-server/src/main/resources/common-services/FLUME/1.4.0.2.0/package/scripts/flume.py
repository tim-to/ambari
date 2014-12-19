"""
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

import glob
import json
import os
from resource_management import *
from resource_management.libraries.functions.flume_agent_helper import is_flume_process_live
from resource_management.libraries.functions.flume_agent_helper import find_expected_agent_names

def flume(action = None):
  import params

  if action == 'config':
    # remove previously defined meta's
    for n in find_expected_agent_names(params.flume_conf_dir):
      os.unlink(os.path.join(params.flume_conf_dir, n, 'ambari-meta.json'))

    Directory(params.flume_conf_dir, recursive=True)
    Directory(params.flume_log_dir, owner=params.flume_user)

    flume_agents = {}
    if params.flume_conf_content is not None:
      flume_agents = build_flume_topology(params.flume_conf_content)

    for agent in flume_agents.keys():
      flume_agent_conf_dir = os.path.join(params.flume_conf_dir, agent)
      flume_agent_conf_file = os.path.join(flume_agent_conf_dir, 'flume.conf')
      flume_agent_meta_file = os.path.join(flume_agent_conf_dir, 'ambari-meta.json')
      flume_agent_log4j_file = os.path.join(flume_agent_conf_dir, 'log4j.properties')
      flume_agent_env_file = os.path.join(flume_agent_conf_dir, 'flume-env.sh')

      Directory(flume_agent_conf_dir)

      PropertiesFile(flume_agent_conf_file,
        properties=flume_agents[agent],
        mode = 0644)

      File(flume_agent_log4j_file,
        content=Template('log4j.properties.j2', agent_name = agent),
        mode = 0644)

      File(flume_agent_meta_file,
        content = json.dumps(ambari_meta(agent, flume_agents[agent])),
        mode = 0644)

      File(flume_agent_env_file,
           owner=params.flume_user,
           content=InlineTemplate(params.flume_env_sh_template)
      )

      if params.has_metric_collector:
        File(os.path.join(flume_agent_conf_dir, "flume-metrics2.properties"),
             owner=params.flume_user,
             content=Template("flume-metrics2.properties.j2")
        )

  elif action == 'start':
    # desired state for service should be STARTED
    if len(params.flume_command_targets) == 0:
      _set_desired_state('STARTED')

    # It is important to run this command as a background process.
    
    
    flume_base = as_user(format("{flume_bin} agent --name {{0}} --conf {{1}} --conf-file {{2}} {{3}}"), params.flume_user, env={'JAVA_HOME': params.java_home}) + " &"

    for agent in cmd_target_names():
      flume_agent_conf_dir = params.flume_conf_dir + os.sep + agent
      flume_agent_conf_file = flume_agent_conf_dir + os.sep + "flume.conf"
      flume_agent_pid_file = params.flume_run_dir + os.sep + agent + ".pid"

      if not os.path.isfile(flume_agent_conf_file):
        continue

      if not is_flume_process_live(flume_agent_pid_file):
        # TODO someday make the ganglia ports configurable
        extra_args = ''
        if params.ganglia_server_host is not None:
          extra_args = '-Dflume.monitoring.type=ganglia -Dflume.monitoring.hosts={0}:{1}'
          extra_args = extra_args.format(params.ganglia_server_host, '8655')
        if params.has_metric_collector:
          extra_args = '-Dflume.monitoring.type=org.apache.hadoop.metrics2.sink.flume.FlumeTimelineMetricsSink'

        flume_cmd = flume_base.format(agent, flume_agent_conf_dir,
           flume_agent_conf_file, extra_args)

        Execute(flume_cmd, 
          wait_for_finish=False,
          environment={'JAVA_HOME': params.java_home}
        )

        # sometimes startup spawns a couple of threads - so only the first line may count
        pid_cmd = format('pgrep -o -u {flume_user} -f ^{java_home}.*{agent}.* > {flume_agent_pid_file}')
        Execute(pid_cmd, logoutput=True, tries=20, try_sleep=6)

    pass
  elif action == 'stop':
    # desired state for service should be INSTALLED
    if len(params.flume_command_targets) == 0:
      _set_desired_state('INSTALLED')

    pid_files = glob.glob(params.flume_run_dir + os.sep + "*.pid")

    if 0 == len(pid_files):
      return

    agent_names = cmd_target_names()


    for agent in agent_names:
      pid_file = params.flume_run_dir + os.sep + agent + '.pid'
      pid = format('`cat {pid_file}` > /dev/null 2>&1')
      Execute(format('kill {pid}'), ignore_failures=True)
      File(pid_file, action = 'delete')


def ambari_meta(agent_name, agent_conf):
  res = {}

  sources = agent_conf[agent_name + '.sources'].split(' ')
  res['sources_count'] = len(sources)

  sinks = agent_conf[agent_name + '.sinks'].split(' ')
  res['sinks_count'] = len(sinks)

  channels = agent_conf[agent_name + '.channels'].split(' ')
  res['channels_count'] = len(channels)

  return res


# define a map of dictionaries, where the key is agent name
# and the dictionary is the name/value pair
def build_flume_topology(content):

  result = {}
  agent_names = []

  for line in content.split('\n'):
    rline = line.strip()
    if 0 != len(rline) and not rline.startswith('#'):
      pair = rline.split('=')
      lhs = pair[0].strip()
      rhs = pair[1].strip()

      part0 = lhs.split('.')[0]

      if lhs.endswith(".sources"):
        agent_names.append(part0)

      if not result.has_key(part0):
        result[part0] = {}

      result[part0][lhs] = rhs

  # trim out non-agents
  for k in result.keys():
    if not k in agent_names:
      del result[k]

  return result


def cmd_target_names():
  import params

  if len(params.flume_command_targets) > 0:
    return params.flume_command_targets
  else:
    return find_expected_agent_names(params.flume_conf_dir)


def _set_desired_state(state):
  import params
  filename = os.path.join(params.flume_run_dir, 'ambari-state.txt')
  File(filename,
    content = state,
  )


def get_desired_state():
  import params

  try:
    with open(os.path.join(params.flume_run_dir, 'ambari-state.txt'), 'r') as fp:
      return fp.read()
  except:
    return 'INSTALLED'
  