#!/usr/bin/python

from ansible.module_utils.basic import *

import subprocess


def main():
    module = AnsibleModule(argument_spec=dict(
        name=dict(required=True, type='str'),
        template=dict(required=True, type='str'),
        parameters=dict(required=False, type='dict'),
    ))

    stack_name = module.params.get('name')

    command = [
        'openstack', 'stack', 'delete',
        '--wait',
    ]

    process = subprocess.Popen(command,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    exit_code = process.wait()
    if exit_code == 0:
        module.exit_json(
            msg="Stack '{}' deployed successfully.".format(stack_name),
            stdout=stdout,
            stderr=stderr,
            rc=exit_code,
            changed=True)
    else:
        module.fail_json(
            msg="Stack '{}' failed.".format(stack_name),
            stdout=stdout,
            stderr=stderr,
            rc=exit_code)

if __name__ == '__main__':
    main()
