# General
The purpose of this project is to properly setup Satellite on OpenStack. It focuses on three areas: Satellite installation and configuration, bootstrapping existing instances and deploying new instances via Heat with automatic bootstrapping.
The aim is to use Heat to do provisioning and then all the systems management: patching, configuration management, insights, etc using Satellite. 
This allows us to bring traditional workloads that are built and then updated through their lifecycle on a cloud platform like OpenStack. Of course for cloud-native workloads that are always rebuilt from scratch with every change you would take a different approach. Point is both approaches are important and getting the traditional one into OpenStack is something a lot of people struggle with greatly.
Satellite is only able to manage Red Hat Enterprise Linux (RHEL) workloads in this way. For other OS's this would not apply.

# Contribution
If you want to provide additional features, please feel free to contribute via pull requests or any other means.
We are happy to track and discuss ideas, topics and requests via 'Issues'.

# Pre-requisites
* Working OpenStack deployment. Tested is OpenStack Pike (12) using RDO.
* RHEL 7 image. Tested is RHEL 7.5.
* An openstack ssh key for accessing instances.
* A pre-configured provider (public) network with at least three available floating ips.
* Additional Flavors configured
  * m2.tiny  (1 vCPU, 1GB RAM, 30 GB Root Disk)
* A router that has the provider network configured as a gateway (floating ip network).
* A internal non-routable network and subnet for instances.
* Properly configured cinder and nova storage.
  * Make sure you aren't using default loop back and have disabled disk zeroing in cinder/nova for LVM.

More information on setting up proper OpenStack environment can be found [here](https://keithtenzer.com/2018/02/05/openstack-12-pike-lab-installation-and-configuration-guide-with-hetzner-root-servers/).

# Blog
I have also created a blog that goes into a bit more detail for those interested
[here]([here](https://keithtenzer.com/2018/06/15/satellite-on-openstack-1-2-3-systems-management-in-the-cloud/))

# Install Satellite
![](images/one.png)
Launch RHEL 7.5 Instance via OpenStack (configure with Floating IP)

Connect to instance and clone github repo
```
# git clone https://github.com/ktenzer/satellite-on-openstack-123.git
```

Configure vars
```
[root@sat6]# cd satellite-openstack-123
```

```
[root@sat6]# cp sample_vars.yml vars.yml
```
```
[root@sat6]# vi vars.yml
```

```
---
### General Settings ###
ssh_user: cloud-user
admin_user: <Satellite admin user>
admin_passwd: <Satellite admin password>

### OpenStack Settings ###
stack_name: myinstance
heat_template_path: /root/satellite-on-openstack-123/heat/instance.yaml
openstack_version: 12
openstack_user: admin
openstack_passwd: <passwd>
openstack_ip: <ip>

### OpenStack Instance Settings ###
hostname: rhel123
domain_name: novalocal
external_network: public
internal_network: internal
internal_subnet: internal-subnet
security_group: base
flavor: m2.tiny
image: rhel75
ssh_key_name: admin
volume_size: 30
ssh_key_name: admin

### Satellite Settings ###
satellite_server: sat6.novalocal
satellite_ip: <ip>
satellite_version: 6.3
activation_key: rhel7-base
puppet_version: puppet4
puppet_environment: KT_RedHat_unstaged_rhel7_base_5
install_puppet: True
puppet_logdir: /var/log/puppet
puppet_ssldir: /var/lib/puppet/ssl
org: <organization>
location: <location>
manifest_file:

### Red Hat Subscription ###
rhn_username: <user>
rhn_password: <password>
rhn_pool: <pool>
```

Configure Inventory File
```
[root@sat6]# cp sample.inventory inventory
```
```
[root@sat6]# vi inventory
[server]
sat6.novalocal

[capsules]

[clients]
rhel2.novalocal
rhel1.novalocal
```

Run Satellite Install Playbook
```
[root@sat6]# ansible-playbook install-satellite.yml \
--private-key=/root/admin.pem -e @.vars.yml -i inventory

PLAY RECAP *****************************************************************************************
rhel1.novalocal : ok=10 changed=4 unreachable=0 failed=0
rhel2.novalocal : ok=10 changed=4 unreachable=0 failed=0
sat6.novalocal : ok=46 changed=18 unreachable=0 failed=0
```

Some things are still not automated. You need to create hostgroup and also configure activation key but that should be it. This is outlined in more detail on my blog.

# Bootstrap Existing Instances
![](images/two.png)
The bootstrap-clients.yml playbook will simply run the sat6-bootstrap role. The role is responsible for connecting an existing instance to Satellite. A good practice in Ansible is to put tasks into roles and make them reusable, I have followed that.

The Satellite bootstrap steps are as follows:

* Install Satellite CA Certificate
* Register to Satellite with activation key
* Install Katello agent
* Start and enable goferd
* Install Red Hat Insights
* Install Puppet
* Configure Puppet

```
[root@sat6]# ansible-playbook bootstrap-clients.yml --private-key=/root/admin.pem -e @../vars.yml -i ../inventory

PLAY RECAP *****************************************************************************************
rhel1.novalocal : ok=8 changed=2 unreachable=0 failed=0
rhel123.novalocal : ok=8 changed=2 unreachable=0 failed=0
```

# Deploy New Instance via Heat and Bootstrap
![](images/three.png)

Configure OpenStack Client

As mentioned in order to communicate with OpenStack we need to authenticate to Keystone, the identity service. The playbook is setup-openstack-client.yml. In order to run it no inventory is needed since it will just configure the client on the localhost or host running playbook.

```
[root@sat6]# ansible-playbook setup-openstack-client.yml --private-key=/root/admin.pem -e @../vars.yml

PLAY RECAP *****************************************************************************************
localhost : ok=4 changed=1 unreachable=0 failed=0
```

Once OpenStack client is setup we need to authenticate. This is done outside of the Ansible environment.

``` 
[root@sat6]# source /root/keystonerc_admin
```

Authentication credentials are set in the environment. We are using OpenStack CLI through Ansible. Another option is to use OpenStack modules written for Ansible and then authentication is of course built-in. This is a much cleaner approach but also requires various python libraries and versions like shade.

Make sure strict ssh host key checking is off (StrictHostKeyChecking) in /etc/sshd/ssh_config or set option on cli for Ansible. If strict host key checking is on you are of course prompted when connecting to host via ssh for first time and automation requires no manual inputs.

```
[root@sat6(keystone_admin)]# export ANSIBLE_HOST_KEY_CHECKING=False
```

Once authenticated run the provision-client.yml playbook. This will take a few minutes, as a new instance in OpenStack will be provisioned.

``` 
[root@sat6(keystone_admin)]# ansible-playbook provision-client.yml \
--private-key=/root/admin.pem -e @../vars.yml
PLAY RECAP *****************************************************************************************
localhost : ok=11 changed=6 unreachable=0 failed=0
rhel3 : ok=15 changed=12 unreachable=0 failed=0
```

If you are configuring puppet, a certificate needs to be signed in Satellite. You can of course setup auto-signed certificates but default is you need to sign. This means pupet agent run will fail. You need to go into Satellite, under Capsule and Certificates. There you can click sign to sign a certificate.


