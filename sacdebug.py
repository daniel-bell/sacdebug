import gdb
import saclib

# A list of lists that represents the local variables of
# the current executed functions
variable_stack = list()
# Breakpoint maps of BP Number -> Function/Variable name
sac_func_bps = dict()  # SACf__ function breakpoints
sac_return_bps = dict()  # SACf__ return breakpoints
sac_var_bps = dict()  # SaC variable watchpoints

# Execution state tracking is required because I couldn't find a method
# of determining it programatically
# 0 = Stopped
# 1 = Stepping
# 2 = Running
old_execution_state = 0
execution_state = 0


def local_vars():
    """ Wrapper around the GDB info locals command"""
    try:
        return_text = gdb.execute("info locals", False, True)
        return return_text
    except gdb.error:
        return ""


def sac_functions():
    """ Returns a list of user defined and overloaded SaC functions"""
    functions_text = gdb.execute("info functions", False, True)

    func_list = [f for f in functions_text.split("\n") if "SACf__" in f]
    func_sigs = [f[f.index(" "):f.index("(")] for f in func_list]
    return func_sigs


class SacVariableWatchpoint(gdb.Breakpoint):
    def __init__(self, spec):
        super(SacVariableWatchpoint, self).__init__(spec, gdb.BP_WATCHPOINT, wp_class=gdb.WP_WRITE, internal=True,
                                                    temporary=True)
        self.silent = True

    def stop(self):
        return True


class SacFunctionBreakpoint(gdb.Breakpoint):
    def __init__(self, spec):
        self.func_name = spec
        super(SacFunctionBreakpoint, self).__init__(spec, gdb.BP_BREAKPOINT, internal=True, temporary=True)
        self.silent = True

    def stop(self):
        return True


class SacFunctionReturnBreakpoint(gdb.FinishBreakpoint):
    def __init__(self, spec):
        self.func_name = spec
        super(SacFunctionReturnBreakpoint, self).__init__(internal=True)
        self.silent = True

    def stop(self):
        return True


class SacInitCommand(gdb.Command):
    """Initialisation command for SaC debugging facilities"""

    def __init__(self):
        global sac_func_bps
        super(SacInitCommand, self).__init__("sacinit", gdb.COMMAND_SUPPORT)

    def invoke(self, arg, from_tty):
        global sac_func_bps
        # Turn off hardware watchpoints because we use way too many
        gdb.execute("set can-use-hw-watchpoints 0")

        func_list = sac_functions()

        print(func_list)
        for func in func_list:
            new_bp = SacFunctionBreakpoint(func)
            sac_func_bps[new_bp.number] = func
            new_bp.silent = True


class SacCommand(gdb.Command):
    """Command for using SaC variables and functions in GDB"""

    def __init__(self):
        super(SacCommand, self).__init__("sac", gdb.COMMAND_SUPPORT)

    def invoke(self, arg, from_tty):
        global execution_state
        global old_execution_state

        if "*sac(" in arg:
            blocks = saclib.extract_sacblocks(arg)

            if not variable_stack:
                current_variables = list()
            else:
                current_variables = variable_stack

            gdb_string = saclib.replace_sacblocks(arg, blocks, current_variables)

            if gdb_string:
                gdb.execute(gdb_string)
            else:
                gdb.write("Error with contents of a *sac() block\n")
        else:
            if arg.strip() == "run":
                old_execution_state = execution_state
                execution_state = 2
                gdb.execute("run", False)
            if arg.strip() == "continue":
                old_execution_state = execution_state
                execution_state = 2
                gdb.execute("continue", False)
            elif arg.strip() == "stop":
                old_execution_state = execution_state
                execution_state = 0
                gdb.execute("stop", False)
            elif arg.strip() == "step":
                old_execution_state = execution_state
                execution_state = 1
                gdb.execute("step", False)


class SacInfoCommand(gdb.Command):
    """Command for retrieving information about sac functions or variables"""

    def __init__(self):
        super(SacInfoCommand, self).__init__("sacinfo", gdb.COMMAND_SUPPORT)

    def invoke(self, arg, from_tty):
        args = arg.strip().split(" ")
        if args[0] == "functions":
            pass
        elif args[0] == "variables":
            pass
        else:
            pass


def breakpoint_handle(event):
    """Function that is called for any breakpoint stop event"""
    global sac_func_bps
    global sac_return_bps
    global sac_var_bps
    global execution_state

    print(sac_return_bps)

    valid_points = 0

    if type(event) is gdb.BreakpointEvent:
        print(event.breakpoints)
        # GDB chains BP stop events if they happen sequentially
        for i, bp in enumerate(event.breakpoints):
            # If the BP is one that has been set at the start of a SaC func
            if bp.number in sac_func_bps:
                var_names = saclib.sac_vars()
                func_name = sac_func_bps[bp.number]

                # Push a new variable frame onto the stack as we've entered a new function
                variable_stack.append(list())
                # Place watchpoints on all local variables
                for var in var_names:
                    new_wp = SacVariableWatchpoint(var)
                    sac_var_bps[new_wp.number] = var

                # Place a breakpoint on the func return statement
                new_finish_bp = SacFunctionReturnBreakpoint(func_name)
                sac_return_bps[new_finish_bp.number] = func_name
                valid_points += 1
            # If the BP is a watchpoint for variable writes
            elif bp.number in sac_var_bps:
                # Push the variable name onto the top frame
                variable_stack[len(variable_stack) - 1].append(sac_var_bps[bp.number])
                print(variable_stack)
                valid_points += 1
                bp.delete()
            # Otherwise if the BP is a function return breakpoint
            elif bp.number in sac_return_bps:
                # TODO: Place another breakpoint on the function entrance
                # Pop the current variable frame
                print("Finish breakpoint")
                variable_stack.pop()
                print(variable_stack)
                valid_points += 1

            # Skip over the amount of system defined BPs encountered
            if valid_points == len(event.breakpoints):
                if execution_state == 0:
                    gdb.execute("continue " + str(valid_points - 1), False)
                    gdb.execute("stop ", False)
                elif execution_state == 1:
                    gdb.execute("step " + str(valid_points - 1), False)
                elif execution_state == 2:
                    gdb.execute("continue " + str(valid_points - 1), False)

# Instantiate commands and setup stop event listener
SacCommand()
SacInitCommand()
gdb.events.stop.connect(breakpoint_handle)