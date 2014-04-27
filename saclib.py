import globals


def find_all(a_str, sub):
    start = 0
    while True:
        start = a_str.find(sub, start)
        if start == -1: return
        yield start
        start += len(sub)


def sac_vars(local_vars):
    """Returns a list of valid SaC local variables"""

    valid_vars = list()

    for line in local_vars.split("\n"):
        if "SACp_emal" in line or "SACl_" in line:
            var_name = line.split(" ")[0].strip()

            # TODO: remove flat

            # Crude removal of array descriptor variables
            array_truth = [True for x in globals.sac_array_exclude if x in var_name]
            if not array_truth:
                valid_vars.append(var_name)

    return valid_vars


def sacvar_to_c(var_name, local_vars):
    """Converts a SaC variable name to the newest C version"""
    valid_vars = list()

    for i, var in enumerate(local_vars):
        if var[:5] == "SACp_":
            underscore_limit = 3
        else:
            underscore_limit = 1

        # Skip the first 2 underscores to get the proper variable name
        signature = ""
        underscores = 0
        for ch in var:
            if underscores < underscore_limit:
                if ch == "_":
                    underscores += 1
            else:
                signature += ch
        valid_vars.append((signature, var))

    # Generate a list of variables that match the var_name
    matched_vars = list()
    sig_size = len(var_name)
    for var in valid_vars:
        match_string = var[0][:sig_size]
        if match_string == var_name:
            matched_vars.append(var[1])

    # If there's more than one variable Single Static Assignment has occurred
    # Sort the list to make sure the highest index contains the latest SSA var

    if matched_vars:
        if len(matched_vars) == 1:
            return matched_vars[0]
        else:
            return sorted(matched_vars)[len(matched_vars) - 1]
    else:
        return None


def cvar_to_sac(var_name, local_vars):
    # Only works if you don't have an _SSA0_ in your variable name
    pass


def sacfunc_to_c(func_name, args=list()):
    """Converts a SaC function signature with optional arguments list to it's C version"""
    sac_namespace = "MAIN"

    # Look for a namespace
    if "::" in func_name:
        # Split the arg by the :: symbol
        sac_namespace = func_name.split("::")[0].upper()
        func_name = func_name.split("::")[1]

    c_func_name = "SACf__" + sac_namespace + "__" + func_name

    # TODO: custom types
    if args:
        for arg in args:
            try:
                arr_starts = find_all(arg, "[")
                arrays = list()
                for start in arr_starts:
                    arg_rest = arg[start + 1:]
                    brackets = 0
                    inner_content = ""
                    for i, ch in enumerate(arg_rest):
                        if ch == "[":
                            brackets += 1
                        elif ch == "]":
                            brackets -= 1
                            if brackets < 1:
                                break
                        inner_content += ch

                    if inner_content.isdigit():
                        arrays.append(int(inner_content))
                    else:
                        if len(inner_content) < 3:
                            arrays.append(0)
                        else:
                            return None

                is_array = True if arrays else False
                c_func_name += "__"

                if is_array:
                    type_string = ""
                    for ch in arg:
                        if ch == "[":
                            break
                        else:
                            type_string += ch
                    arg_type = globals.sac_types[type_string]
                else:
                    arg_type = globals.sac_types[arg]

                c_func_name += arg_type

                for arr in arrays:
                    if arr > 0:
                        c_func_name += ("_" + str(arr))
                    else:
                        c_func_name += "_P"
            except KeyError:
                return None

    return c_func_name


def extract_sacblocks(arg):
    """ Extracts the *sac() block contents from a string as well as the start & end indexes"""
    start_indexes = find_all(arg, "*sac(")

    commands = list()
    for s_index in start_indexes:
        # Pull the inside of the *sac( commands into a string
        # Includes bracket matching to
        string_end = arg[s_index + len("*sac("):]
        brackets = 1
        inner_content = ""
        end_bracket_index = 0
        for i, ch in enumerate(string_end):
            if ch == "(":
                brackets += 1
            elif ch == ")":
                brackets -= 1
                if brackets < 1:
                    end_bracket_index = i
                    break
            inner_content += ch

        end_index = s_index + end_bracket_index + len("*sac(")
        commands.append((s_index, end_index, inner_content))

    return commands


def replace_sacblocks(arg, sacblocks, local_vars):
    """ Replace *sac() blocks in a string with their C equivalents """
    if sacblocks:
        gdb_command = arg[:sacblocks[0][0]]

        for i, block in enumerate(sacblocks):
            if i > 1:
                gdb_command += arg[sacblocks[i - 1][1]:block[0]]

            sac_command = sac_to_c(block[2], local_vars)
            if sac_command:
                gdb_command += sac_command
            else:
                return None

        return gdb_command


def sac_to_c(arg, local_vars):
    """Converts a SaC variable or function to it's C equivalent"""
    symbol = ""
    func_args = ""
    is_function = False

    # Loop over the arg and determine if it's a variable or function
    for i, ch in enumerate(arg):
        # Variables and functions must start with a non-numeric char
        if i == 0 and ch.isdigit():
            return None
        # If opening parenthesis found and not the first char then this is a valid function
        if ch == "(":
            if i > 0:
                is_function = True
            else:
                return None
        # If there's no opening parenthesis then return error if closing one found
        elif ch == ")":
            if is_function:
                break
            else:
                return None
        else:
            if not is_function:
                symbol += ch
            else:
                func_args += ch

    arg_list = [arg.strip() for arg in func_args.split(",") if arg.strip()]

    if not is_function:
        return sacvar_to_c(symbol, sac_vars(local_vars))
    else:
        return sacfunc_to_c(symbol, arg_list)