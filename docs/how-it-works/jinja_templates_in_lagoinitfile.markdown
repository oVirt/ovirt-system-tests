OST uses [lago] to bootstrap the architecture to run its test on, using LagoInitFile.

Essentially it is a yml file with definitions, here is and example of definition of (virtual) host:

```yml
host-0:
  vm-type: ovirt-host
  memory: 2047
```

This will create 1 vm with 2047 ram, with the assigned name 'host-0'. If we want 100 hosts or
to have some of definitions parameterized, we use [jinja template language](jinja) to pre-process the yml file.

### Using Jinja templates

`run-suite.sh`, the entrypoint to run a suite, will take `LagoInitfile.in` and consume it as a [jinja] template, and output
an interpolated yml file. This means we can use all sort of jinja expressions, here's couple of examples.

### Jinja variables and 'env'
Lets use a simple jinja expression to create a unique host name using environment variable. The [trick] is done by
'run-suite.sh' scripts that render jinja template and loads all the shell environment into global variable 'env',
 that is accessible to jinja expressions in the template.

Here's how to use it to give a special name to a host:
```yml
# export suite_name=integ-tests
# cat LagoInitFile.in
{{ env.suite_name }}-host-0:    # integ-tests-host-0:
  vm-type: ovirt-host
```

### jinja Loops
If we want 100 hosts, use jinja loops expression:
```yml
{% for i in range(100) %}
  {{ env.suite_name }}-host-{{ i }}:
    vm-type: ovirt-host
{% endfor %}

```

### Load vars into the template context
By default jinja will loads `vars/main.yml` and load it into rendering context, similar to how it is done with environment
 variables.
 
 ```yml
 # cat vars/main.yml
 hostCount: 100
 ```
 
 Now this expression loops 100 times:
 ```yml
 {% for i in range(hostCount) %} ...
 ```


### How it is done
There is a mini common python script, that invokes the template engine on the LagoInitFile.in and outputs the final file
 with first loading the environment and vars/main.yml demonstrated before. It is recommended that all suites will do the same, it 
 requires nothing more than pointing the control.sh script to load in the `pre_suite` section:
 
 ```bash
prep_suite () {
    render_jinja_templates
}
```

[lago]: http://lago.readthedocs.io/en/stable/
[jinja]: http://jinja.pocoo.org/
[trick]: https://gerrit.ovirt.org/gitweb?p=ovirt-system-tests.git;a=blob;f=common/scripts/render_jinja_templates.py;h=e8668cc16dd9d67a12b3e30ad87d7d62bcc14c10;hb=ba2de49374f2742e40e3fd53f520fd2404b4b3d4
