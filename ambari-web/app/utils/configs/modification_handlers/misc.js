/**
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements. See the NOTICE file distributed with this
 * work for additional information regarding copyright ownership. The ASF
 * licenses this file to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 * http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 */

var App = require('app');
require('utils/configs/modification_handlers/modification_handler');

module.exports = App.ServiceConfigModificationHandler.create({
  serviceId : 'MISC',
  getDependentConfigChanges : function(changedConfig, selectedServices, allConfigs, securityEnabled) {
    var affectedProperties = [];
    var newValue = changedConfig.get("value");
    var curConfigs = "";
    var affectedPropertyName = "dfs.permissions.superusergroup";
    if (changedConfig.get("name") == "hdfs_user") {
      curConfigs = allConfigs.findProperty("serviceName", "HDFS").get("configs");
      if (newValue != curConfigs.findProperty("name", affectedPropertyName).get("value")) {
        affectedProperties.push({
          serviceName : "HDFS",
          sourceServiceName : "MISC",
          propertyName : affectedPropertyName,
          propertyDisplayName : affectedPropertyName,
          newValue : newValue,
          curValue : curConfigs.findProperty("name", affectedPropertyName).get("value"),
          changedPropertyName : "hdfs_user",
          remove : false,
          filename : 'hdfs-site.xml'
        });
      }
      if ($.trim(newValue) != $.trim(curConfigs.findProperty("name", "dfs.cluster.administrators").get("value"))) {
        affectedProperties.push({
          serviceName : "HDFS",
          sourceServiceName : "MISC",
          propertyName : "dfs.cluster.administrators",
          propertyDisplayName : "dfs.cluster.administrators",
          newValue : " " + $.trim(newValue),
          curValue : curConfigs.findProperty("name", "dfs.cluster.administrators").get("value"),
          changedPropertyName : "hdfs_user",
          remove : false,
          filename : 'hdfs-site.xml'
        });
      }
    } else if (changedConfig.get("name") == "user_group") {
      if (!(selectedServices.indexOf("YARN") >= 0)) {
        return;
      }
      if (selectedServices.indexOf("MAPREDUCE2") >= 0) {
        curConfigs = allConfigs.findProperty("serviceName", "MAPREDUCE2").get("configs");
        if ($.trim(newValue) != $.trim(curConfigs.findProperty("name", "mapreduce.cluster.administrators").get("value"))) {
          affectedProperties.push({
            serviceName : "MAPREDUCE2",
            sourceServiceName : "MISC",
            propertyName : "mapreduce.cluster.administrators",
            propertyDisplayName : "mapreduce.cluster.administrators",
            newValue : " " + $.trim(newValue),
            curValue : curConfigs.findProperty("name", "mapreduce.cluster.administrators").get("value"),
            changedPropertyName : "user_group",
            filename : 'mapred-site.xml'
          });
        }
      }
      if (selectedServices.indexOf("YARN") >= 0) {
        curConfigs = allConfigs.findProperty("serviceName", "YARN").get("configs");
        if (newValue != curConfigs.findProperty("name", "yarn.nodemanager.linux-container-executor.group").get("value")) {
          affectedProperties.push({
            serviceName : "YARN",
            sourceServiceName : "MISC",
            propertyName : "yarn.nodemanager.linux-container-executor.group",
            propertyDisplayName : "yarn.nodemanager.linux-container-executor.group",
            newValue : newValue,
            curValue : curConfigs.findProperty("name", "yarn.nodemanager.linux-container-executor.group").get("value"),
            changedPropertyName : "user_group",
            filename : 'yarn-site.xml'
          })
        }
      }
    }
    return affectedProperties;
  }
});