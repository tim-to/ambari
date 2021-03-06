#!/usr/bin/env python
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

import sys
from storm import storm
from service import service
from supervisord_service import supervisord_service, supervisord_check_status
from resource_management.libraries.script import Script
from resource_management.libraries.functions import conf_select
from resource_management.libraries.functions import hdp_select
from resource_management.libraries.functions import format
from resource_management.core.resources.system import Execute
from resource_management.libraries.functions.version import compare_versions, format_hdp_stack_version


class Supervisor(Script):

  def get_stack_to_component(self):
    return {"HDP": "storm-supervisor"}

  def install(self, env):
    self.install_packages(env)
    self.configure(env)

  def configure(self, env):
    import params
    env.set_params(params)
    storm()

  def pre_rolling_restart(self, env):
    import params
    env.set_params(params)

    if params.version and compare_versions(format_hdp_stack_version(params.version), '2.2.0.0') >= 0:
      conf_select.select(params.stack_name, "storm", params.version)
      hdp_select.select("storm-supervisor", params.version)

  def start(self, env, rolling_restart=False):
    import params
    env.set_params(params)
    self.configure(env)

    supervisord_service("supervisor", action="start")
    service("logviewer", action="start")

  def stop(self, env, rolling_restart=False):
    import params
    env.set_params(params)

    supervisord_service("supervisor", action="stop")
    service("logviewer", action="stop")

  def status(self, env):
    supervisord_check_status("supervisor")

if __name__ == "__main__":
  Supervisor().execute()
