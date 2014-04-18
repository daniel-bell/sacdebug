import gdb
import string

# A list of lists that represents the local variables of
# the current executed functions
variable_stack = list()
# Breakpoint maps of BP Number -> Function/Variable name
sac_func_bps = dict()  # SACf__ function breakpoints
sac_return_bps = dict()  # SACf__ return breakpoints
sac_var_bps = dict()  # SaC variable watchpoints

# Map of SaC types to their overloaded function identifiers
# User defined types are mapped to SACt__NAMESPACE__typename
sac_types = {"int": "i", "float": "f", "double": "d", "bool": "b"}

# SaC array descriptor variables (shape, size etc)
# If the variable referenced exists and is a pointer
# then these are ignored
sac_array_exclude = {"__sz", "__dim", "__desc", "__shp"}


def sac_vars():
    """Returns a list of valid SaC local variables"""
    locals_text = gdb.execute("info locals", False, True)
    valid_vars = list()

    for line in locals_text.split("\n"):
        if "SACp_emal" in line or "SACl_" in line:
            var_name = line.split(" ")[0].strip()

            # TODO Get rid of array descriptor variables
            # Check existence and type of host variable
            valid_vars.append(var_name)

    return valid_vars


def sac_functions():
    """ Returns a list of user defined and overloaded SaC functions"""
    functions_text = gdb.execute("info functions")
    # Pull the SACf__ function signatures into a list
    func_sig_list = [func_name.strip() for func_name in functions_text.split("\n") if "SACf__" == func_name[:6]]
    # Retrieve only the function name from the signatures into a new list
    func_list = [func[func.index(" ") + 1: func.index("(")] for func in func_sig_list]
    return func_list


def sacvar_to_c(var_name, local_vars):
    """Converts a SaC variable name to the newest C version"""
    # Caveat: if __SSA0_ is included in a SaC variable name then this all fails
    underscores = 0
    valid_vars = list()

    for var in local_vars:
        # Skip the first 3 underscores to get the proper function signature
        signature = ""
        for ch in var:
            if underscores < 3:
                if ch == "_":
                    underscores += 1
            else:
                signature += ch
        valid_vars.append(signature)

    # TODO Check var_name against valid_vars
    # If there's more than one variable Single Static Assignment has occured
    # Sort the list to make sure the highest index contains the latest SSA var
    if len(valid_vars) == 1:
        return valid_vars[0]
    else:
        return sorted(valid_vars)[len(valid_vars)]


def sacfunc_to_c(func_name, args=list()):
    """Converts a SaC function signature with optional arguments list to it's C version"""
    sac_namespace = "MAIN"

    # Look for a namespace
    if "::" in func_name:
        # Split the arg by the :: symbol
        sac_namespace = func_name.split("::")[0].upper()
        func_name = func_name.split("::")[1]

    c_func_name = "SACf__" + sac_namespace + "__" + func_name

    # TODO argument conversion for overloading
    if args:
        pass

    return c_func_name


def sac_to_c(arg):
    """Converts a SaC variable or function to it's C equivalent"""
    symbol = ""
    func_args = ""
    is_function = False

    # Loop over the arg and determine if it's a variable or function
    for i, ch in enumerate(arg):
        # Variables and functions must start with a non-numeric char
        if i == 0 and ch.isdigit():
            gdb.Write("Error - SaC functions and variables cannot start with a digit")
            return None
        # If opening paranthesis found and not the first char then this is a valid function
        if ch == "(":
            if i > 0:
                is_function = True
            else:
                gdb.Write("Error - SaC function names must be at least one character long")
                return None
        # If there's no opening paranthesis then return error if closing one found
        if ch == ")" and not is_function:
            gdb.Write("Error - Misplace closing parenthesis")
            return None

        if not is_function:
            symbol += ch
        else:
            func_args += ch

    print(symbol)
    print(func_args)

    if not is_function:
        print("Variable found")
        return sacvar_to_c(symbol, sac_vars())
    else:
        print("Function found")
        return sacfunc_to_c(symbol, func_args)


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


class SacDebugCommand(gdb.Command):
    """Command used for performing SaC functions"""
    
    def __init(self):
        super(SacDebugCommand, self).__init__("sac", gdb.COMMAND_SUPPORT)

    def invoke(self, arg, from_tty):
        pass


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
        super().__init__("sac", gdb.COMMAND_SUPPORT)

    def invoke(self, arg, from_tty):
        if "_sac(" in arg:
            pass


def breakpoint_handle(event):
    """Function that is called for any breakpoint stop event"""
    global sac_func_bps
    global sac_return_bps
    global sac_var_bps

    print(sac_return_bps)

    valid_points = 0

    if type(event) is gdb.BreakpointEvent:
        print(event.breakpoints)
        # GDB chains BP stop events if they happen sequentially
        for i, bp in enumerate(event.breakpoints):
            # If the BP is one that has been set at the start of a SaC func
            if bp.number in sac_func_bps:
                var_names = sac_vars()
                func_name = sac_func_bps[bp.number]

                # Push a new variable frame onto the stack as we've entered a new function
                variable_stack.append(list())
                # Place watchpoints on all local variables
                for var in var_names:
                    new_wp = SacVariableWatchpoint(var, func_name)
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
                # Pop the current variable frame
                print("Finish breakpoint")
                variable_stack.pop()
                print(variable_stack)
                valid_points += 1

            # Skip over the amount of system defined BPs encountered
            if valid_points == len(event.breakpoints):
                print("continuing " + str(valid_points))
                gdb.execute("step")
                # gdb.execute("continue " + str(valid_points - 1))

# Instantiate commands and setup stop event listener
SacCommand()
SacInitCommand()
gdb.events.stop.connect(breakpoint_handle)