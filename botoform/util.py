import yaml
import json
import boto3

class BotoConnections(object):
    """Central Management of boto3 client and resource connection objects."""
    def __init__(self, region_name=None, profile_name=None):
        """
        Optionally pass region_name and profile_name. Setup boto3 session.
        Attach boto3 client and resource connection objects.
        """
        # trigger region_name.setter
        self.region_name = region_name
        # trigger profile_name.setter
        self.profile_name = profile_name

    @property
    def profile_name(self):
        return self._profile_name

    @profile_name.setter
    def profile_name(self, new_name):
        """set profile_name and refresh_boto_connections"""
        self._profile_name = new_name
        if new_name is not None:
            boto3.setup_default_session(profile_name = new_name)
        self.refresh_boto_connections()

    @property
    def region_name(self):
        return self._region_name

    @region_name.setter
    def region_name(self, new_name):
        """set region_name and refresh_boto_connections"""
        self._region_name = new_name
        self.refresh_boto_connections()

    def refresh_boto_connections(self):
        """Attach related Boto3 clients and resources."""
        self.ec2 = boto3.resource('ec2', region_name = self.region_name)
        self.rds = boto3.client('rds', region_name = self.region_name)
        self.elasticache = boto3.client('elasticache', region_name = self.region_name)


class BotoformDumper(yaml.Dumper):
    """A custom YAML dumper that is pretty."""
    def increase_indent(self, flow=False, indentless=False):
        return super(BotoformDumper, self).increase_indent(flow, False)


class Log(object):
    """Handles emitting logs to syslog and stdout."""
    def __init__(self, desired_level='debug', syslog=True, stdout=True, program='botoform'):
        """
        Setup Log object with desired parameters

        desired_level:
          The lowest severity level to log (default debug).

        stdout:
          Boolean to determine if messages should emit to STDOUT (default True).

        stdout:
          Boolean to determine if messages should emit to syslog (default True).

        program:
          The program field used by syslog (default botoform).
        """
        # order matters.
        self.all_levels  = ['debug', 'info', 'warning', 'error']
        self.desired_level = desired_level
        self.stdout  = stdout
        self.syslog  = syslog
        self.program = program

    @property
    def levels(self):
        """Return a list of levels on and beyond desired_level."""
        return self.all_levels[self.all_levels.index(self.desired_level):]

    def emit(self, message, level='info'):
        """
        Emit message if level meets requirement.

        message:
          Any object that has a __str__ method.

        level:
          The level or severity of this message (default info)
        """
        if level not in self.levels:
            return False

        if self.stdout == True:
            print(message)

        if self.syslog == True:
            # TODO: some sysloggy stuff here.
            pass

        return True


def output_formatter(data, output_format='newline'):
    """Print data in the optional output_format."""
    if output_format.lower() == 'newline':
        output = '\n'.join(data)
    elif output_format.upper() == 'CSV':
        output = ', '.join(data)
    elif output_format.upper() == 'YAML':
        output = yaml.dump(data, Dumper=BotoformDumper)
    elif output_format.upper() == 'JSON':
        output = json.dumps(data, indent=2)
    return output

def reflect_attrs(child, parent):
    """Composition Magic: reflect all missing parents attributes into child."""
    existing = dir(child)
    for attr in dir(parent):
        if attr not in existing:
            child.__dict__[attr] = getattr(parent, attr)

def make_tag_dict(ec2_object):
    """Given an tagable ec2_object, return dictionary of existing tags."""
    tag_dict = {}
    if ec2_object.tags is None: return tag_dict
    for tag in ec2_object.tags:
        tag_dict[tag['Key']] = tag['Value']
    return tag_dict

def update_tags(ec2_object, **kwargs):
    """Given a tagable ec2_object, add or update tags to reflect keyword args"""
    tags_to_update = []
    tag_dict = make_tag_dict(ec2_object)
    for key, value in kwargs.iteritems():
        if tag_dict.get(key, None) != value:
            tags_to_update.append({'Key' : key, 'Value' : value})
    ec2_object.create_tags(Tags = tags_to_update)

def dict_to_key_value(data, sep='=', pair_sep=','):
    """turns {'key1':'value1','key2':'value2'} into key1=value1,key2=value2"""
    return pair_sep.join([sep.join(key_value) for key_value in data.items()])

def key_value_to_dict(key_value_list, sep='=', pair_sep=','):
    """
    Accept a key_value_list, like::

      key_value_list = ['a=1,b=2', 'c=3, d=4', 'e=5']

    Return a dict, like::

      {'a':'1', 'b':'2', 'c':'3', 'd':'4', 'e':'5'}
    """
    d = {}
    # allow user to pass a string or a list of strings.
    if isinstance(key_value_list, str): key_value_list = [key_value_list]
    for speclist in key_value_list:
        for spec in speclist.strip().split(','):
            key, value = spec.strip().split('=')
            d[key] = value
    return d
