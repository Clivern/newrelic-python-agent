import atexit
import cmd
import code
import ConfigParser
import functools
import glob
import inspect
import optparse
import os
import shlex
import socket
import sys
import threading
import traceback
import os

import __builtin__

from newrelic.core.agent import agent_instance
from newrelic.core.config import global_settings, flatten_settings
from newrelic.api.transaction import Transaction
from newrelic.api.object_wrapper import ObjectWrapper

def shell_command(wrapped):
    args, varargs, keywords, defaults = inspect.getargspec(wrapped)

    parser = optparse.OptionParser()
    for name in args[1:]:
        parser.add_option('--%s' % name, dest=name)

    @functools.wraps(wrapped)
    def wrapper(self, line):
        result = shlex.split(line)

        (options, args) = parser.parse_args(result)

        kwargs = {}
        for key, value in options.__dict__.items():
            if value is not None:
                kwargs[key] = value

        return wrapped(self, *args, **kwargs)

    if wrapper.__name__.startswith('do_'):
        prototype = wrapper.__name__[3:] + ' ' + inspect.formatargspec(
                args[1:], varargs, keywords, defaults)
        if hasattr(wrapper, '__doc__') and wrapper.__doc__ is not None:
            wrapper.__doc__ = '\n'.join((prototype,
                    wrapper.__doc__.lstrip('\n')))

    return wrapper

_consoles = threading.local()

def acquire_console(shell):
    _consoles.active = shell

def release_console():
    del _consoles.active

def setquit():
    """Define new built-ins 'quit' and 'exit'.
    These are simply strings that display a hint on how to exit.

    """
    if os.sep == ':':
        eof = 'Cmd-Q'
    elif os.sep == '\\':
        eof = 'Ctrl-Z plus Return'
    else:
        eof = 'Ctrl-D (i.e. EOF)'

    class Quitter(object):
        def __init__(self, name):
            self.name = name

        def __repr__(self):
            return 'Use %s() or %s to exit' % (self.name, eof)

        def __call__(self, code=None):
            # If executed with our interactive console, only raise the
            # SystemExit exception but don't close sys.stdout as we are
            # not the owner of it.

            if hasattr(_consoles, 'active'):
                raise SystemExit(code)

            # Shells like IDLE catch the SystemExit, but listen when their
            # stdin wrapper is closed.

            try:
                sys.stdin.close()
            except:
                pass
            raise SystemExit(code)

    __builtin__.quit = Quitter('quit')
    __builtin__.exit = Quitter('exit')

class OutputWrapper(ObjectWrapper):

    def flush(self):
        try:
            shell = _consoles.active
            return shell.stdout.flush()
        except:
            return self._nr_next_object.flush()

    def write(self, data):
        try:
            shell = _consoles.active
            return shell.stdout.write(data)
        except:
            return self._nr_next_object.write(data)

    def writelines(self, data):
        try:
            shell = _consoles.active
            return shell.stdout.writelines(data)
        except:
            return self._nr_next_object.writelines(data)

def intercept_console():
    setquit()

    sys.stdout = OutputWrapper(sys.stdout, None, None)
    sys.stderr = OutputWrapper(sys.stderr, None, None)

class EmbeddedConsole(code.InteractiveConsole):

    def write(self, data):
        self.stdout.write(data)
        self.stdout.flush()

    def raw_input(self, prompt):
        self.stdout.write(prompt)
        self.stdout.flush()
        line = self.stdin.readline()
        line = line.rstrip('\r\n')
        return line

class ConsoleShell(cmd.Cmd):

    use_rawinput = 0

    def __init__(self):
        cmd.Cmd.__init__(self)
        self.do_prompt('on')

    def emptyline(self):
        pass

    def help_help(self):
        print >> self.stdout, """help (command)
        Output list of commands or help details for named command."""

    @shell_command
    def do_prompt(self, flag=None):
        """
        Enable or disable the console prompt."""

        if flag == 'on':
            self.prompt = '(newrelic:%d) ' % os.getpid()
        elif flag == 'off':
            self.prompt = ''

    @shell_command
    def do_exit(self):
        """
        Exit the console."""

        return True

    @shell_command
    def do_sys_prefix(self):
        """
        Displays the value of sys.prefix."""

        print >> self.stdout, sys.prefix

    @shell_command
    def do_sys_path(self):
        """
        Displays the value of sys.path."""

        print >> self.stdout, sys.path

    @shell_command
    def do_sys_modules(self):
        """
        Displays the list of Python modules loaded."""

        for name, module in sorted(sys.modules.items()):
            if module is not None:
                file = getattr(module, '__file__', None)
                print >> self.stdout, "%s - %s" % (name, file)

    @shell_command
    def do_os_environ(self):
        """
        Displays the set of user environment variables."""

        for key, name in os.environ.items():
            print >> self.stdout, "%s = %r" % (key, name)

    @shell_command
    def do_config_args(self):
        """
        Displays the configure arguments used to build Python."""

        args = ''

        try:
            # This may fail if using package Python and the
            # developer package for Python isn't also installed.

            import distutils.sysconfig

            args = distutils.sysconfig.get_config_var('CONFIG_ARGS')

        except:
            pass

        print >> self.stdout, args

    @shell_command
    def do_dump_config(self, name=None):
        """
        Displays global configuration or that of the named application.
        """

        if name is None:
            config = agent_instance().global_settings()
        else:
            config = agent_instance().application_settings(name)

        if config is not None:
            config = flatten_settings(config)
            keys = sorted(config.keys())
            for key in keys:
                print >> self.stdout, '%s = %r' % (key, config[key])

    @shell_command
    def do_agent_status(self):
        """
        Displays general status information about the agent, registered
        applications, harvest cycles etc.
        """

        agent_instance().dump(self.stdout)

    @shell_command
    def do_applications(self):
        """
        Displays a list of the applications.
        """

        print >> self.stdout, repr(sorted(
              agent_instance().applications.keys()))

    @shell_command
    def do_application_status(self, name):
        """
        Displays general status information about an application, last
        harvest cycle, etc.
        """

        application = agent_instance().application(name)
        if application is not None:
            application.dump(self.stdout)

    @shell_command
    def do_transactions(self):
        """
        """

        for transaction in Transaction._transactions.values():
            transaction.dump(self.stdout)
            print >> self.stdout

    @shell_command
    def do_interpreter(self):
        """
        When enabled in the configuration file, will startup up an embedded
        interactive Python interpreter. Invoke 'exit()' or 'quit()' to
        escape the interpreter session."""

        enabled = False

        _settings = global_settings()

        if not _settings.console.allow_interpreter_cmd:
            print >> self.stdout, 'Sorry, the embedded Python ' \
                    'interpreter is disabled.'
            return

        locals = {}

        locals['stdin'] = self.stdin
        locals['stdout'] = self.stdout

        console = EmbeddedConsole(locals)

        console.stdin = self.stdin
        console.stdout = self.stdout

        acquire_console(self)

        try:
            console.interact()
        except SystemExit:
            pass
        finally:
            release_console()

    @shell_command
    def do_threads(self): 
        """
        Display stack trace dumps for all threads currently executing
        within the Python interpreter.

        Note that if coroutines are being used, such as systems based
        on greenlets, then only the thread stack of the currently
        executing coroutine will be displayed."""

        all = [] 
        for threadId, stack in sys._current_frames().items():
            block = []
            block.append('# ThreadID: %s' % threadId) 
            thr = threading._active.get(threadId)
            if thr:
                block.append('# Name: %s' % thr.name) 
            for filename, lineno, name, line in traceback.extract_stack(
                stack): 
                block.append('File: \'%s\', line %d, in %s' % (filename,
                        lineno, name)) 
                if line:
                    block.append('  %s' % (line.strip()))
            all.append('\n'.join(block))

        print >> self.stdout, '\n\n'.join(all)

class ConnectionManager(object):

    def __init__(self, listener_socket):
        self.__listener_socket = listener_socket
        self.__console_initialized = False

        if not os.path.isabs(self.__listener_socket):
            host, port = self.__listener_socket.split(':')
            port = int(port)
            self.__listener_socket = (host, port)

        self.__thread = threading.Thread(target=self.__thread_run,
            name='NR-Console-Manager')

        self.__thread.setDaemon(True)
        self.__thread.start()

    def __socket_cleanup(self, path):
        try:
            os.unlink(path)
        except:
            pass

    def __thread_run(self):
        if type(self.__listener_socket) == type(()):
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(self.__listener_socket)
        else:
            try:
                os.unlink(self.__listener_socket)
            except:
                pass

            listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            listener.bind(self.__listener_socket)

            atexit.register(self.__socket_cleanup, self.__listener_socket)
            os.chmod(self.__listener_socket, 0600)

        listener.listen(5)

        while True:
            client, addr = listener.accept()

            if not self.__console_initialized:
                self.__console_initialized = True
                intercept_console()

            shell = ConsoleShell()

            shell.stdin = client.makefile('r')
            shell.stdout = client.makefile('w')

            while True:
                try:
                    shell.cmdloop()

                except:
                    shell.stdout.flush()
                    print >> shell.stdout, 'Unexpected exception.'
                    exc_info = sys.exc_info()
                    traceback.print_exception(exc_info[0], exc_info[1],
                            exc_info[2], file=shell.stdout)
                    exc_info = None

                else:
                    break

            shell.stdin = None
            shell.stdout = None

            del shell

            client.close()

class ClientShell(cmd.Cmd):

    prompt = '(newrelic) '

    def __init__(self, config_file, stdin=None, stdout=None):
        cmd.Cmd.__init__(self, stdin=stdin, stdout=stdout)

        self.__config_file = config_file
        self.__config_object = ConfigParser.RawConfigParser()

        if not self.__config_object.read([config_file]):
            raise RuntimeError('Unable to open configuration file %s.' %
                               config_file)

        listener_socket = self.__config_object.get('newrelic',
                'console.listener_socket') % {'pid': '*'}

        if os.path.isabs(listener_socket):
            self.__servers = [(socket.AF_UNIX, path) for path in
                             sorted(glob.glob(listener_socket))]
        else:
            host, port = listener_socket.split(':')
            port = int(port)

            self.__servers = [(socket.AF_INET, (host, port))]

    def emptyline(self):
        pass

    def help_help(self):
        print >> self.stdout, """help (command)
        Output list of commands or help details for named command."""

    def do_exit(self, line):
        """exit
        Exit the client shell."""

        return True

    def do_servers(self, line):
        """servers
        Display a list of the servers which can be connected to."""

        for i in range(len(self.__servers)):
            print >> self.stdout, '%s: %s' % (i+1, self.__servers[i])

    def do_connect(self, line):
        """connect [index]
        Connect to the server from the servers lift with given index. If
        there is only one server then the index position does not need to
        be supplied."""

        if len(self.__servers) == 0:
            print >> self.stdout, 'No servers to connect to.'
            return

        if not line:
            if len(self.__servers) != 1:
                print >> self.stdout, 'Multiple servers, which should be used?'
                return
            else:
                line = '1'

        try:
            selection = int(line)
        except:
            selection = None

        if selection is None:
            print >> self.stdout, 'Server selection not an integer.'
            return

        if selection <= 0 or selection > len(self.__servers):
            print >> self.stdout, 'Invalid server selected.'
            return

        server = self.__servers[selection-1]

        client = socket.socket(server[0], socket.SOCK_STREAM)
        client.connect(server[1])

        def write():
            while 1:
                try:
                    c = sys.stdin.read(1)
                    if not c:
                        client.shutdown(socket.SHUT_RD)
                        break
                    client.sendall(c)
                except:
                    break

        def read():
            while 1:
                try:
                    c = client.recv(1)
                    if not c:
                        break
                    sys.stdout.write(c)
                    sys.stdout.flush()
                except:
                    break

        thread1 = threading.Thread(target=write)
        thread1.setDaemon(True)

        thread2 = threading.Thread(target=read)
        thread2.setDaemon(True)

        thread1.start()
        thread2.start()

        thread2.join()

        return True

def main():
    if len(sys.argv) == 1:
        print "Usage: newrelic-console config_file"
        sys.exit(1)

    shell = ClientShell(sys.argv[1])
    shell.cmdloop()

if __name__ == '__main__':
    main()
