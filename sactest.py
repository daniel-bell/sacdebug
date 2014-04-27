import saclib
import unittest


class TestUtilityFunctions(unittest.TestCase):
    def setUp(self):
        pass

    def test_find_all(self):
        test_arr = "test test test"
        result_arr = list(saclib.find_all(test_arr, "test"))
        self.assertEqual(result_arr, [0, 5, 10])


class TestStackFrames(unittest.TestCase):
    def setUp(self):
        pass


class TestLocalVars(unittest.TestCase):
    def setup(self):
        pass

    def test_sac_vars(self):
        input_vars = "SACp_emal_5_x\nSACp_emal_5_x__SSA01\nSACl_foo\nSACf__MAIN__foo"
        expected_result = ["SACp_emal_5_x", "SACp_emal_5_x__SSA01", "SACl_foo"]
        result = saclib.sac_vars(input_vars)
        self.assertEqual(expected_result, result)


class TestVariableConversion(unittest.TestCase):
    def setUp(self):
        pass

    def test_sac_to_c(self):
        input_locals = ["SACp_emal_5_x", "SACp_emal_5_x__SSA0_1", "SACl_foo"]
        input_var = "foo"
        self.assertEqual(saclib.sacvar_to_c(input_var, input_locals), "SACl_foo")
        input_var = "x"
        self.assertEqual(saclib.sacvar_to_c(input_var, input_locals), "SACp_emal_5_x__SSA0_1")

        input_locals = ["SACp_emal_5_x", "SACp_emal_5_x__SSA0_1", "SACp_emal_79_x__SSA0_2", "SACl_foo"]
        input_var = "x"
        self.assertEqual(saclib.sacvar_to_c(input_var, input_locals), "SACp_emal_79_x__SSA0_2")

        input_locals = ["SACp_emal_5_x", "SACl_foo"]
        input_var = "x"
        self.assertEqual(saclib.sacvar_to_c(input_var, input_locals), "SACp_emal_5_x")

    def test_c_to_sac(self):
        pass


class TestFunctionConversion(unittest.TestCase):
    def setUp(self):
        pass

    def test_sac_to_c(self):
        # Test conversion of function signatures with no arguments
        self.assertEqual(saclib.sacfunc_to_c("foo", []), "SACf__MAIN__foo")
        # Test specifying the namespace of a function
        self.assertEqual(saclib.sacfunc_to_c("foo::bar", []), "SACf__FOO__bar")

        # Test scalar arguments
        self.assertEqual(saclib.sacfunc_to_c("foo::bar", ["int", "int"]), "SACf__FOO__bar__i__i")
        self.assertEqual(saclib.sacfunc_to_c("foo::bar", ["int", "float"]), "SACf__FOO__bar__i__f")

        # Test array arguments
        self.assertEqual(saclib.sacfunc_to_c("foo::bar", ["int[]", "int"]), "SACf__FOO__bar__i_i__i")
        # Test multi-dimensional array arguments
        self.assertEqual(saclib.sacfunc_to_c("foo::bar", ["int[][]", "float[]"]), "SACf__FOO__bar__i_i_i__f_f")
        self.assertEqual(saclib.sacfunc_to_c("foo::bar", ["int[][][]", "float[][]"]), "SACf__FOO__bar__i_i_i_i__f_f_f")

        # Test fixed size array arguments
        self.assertEqual(saclib.sacfunc_to_c("foo::bar", ["int[6]", "int"]), "SACf__FOO__bar__i_6__i")
        self.assertEqual(saclib.sacfunc_to_c("foo::bar", ["int[][6]", "int"]), "SACf__FOO__bar__i_i_6__i")

        # Test invalid argument type
        self.assertEqual(saclib.sacfunc_to_c("foo::bar", ["int", "foo"]), None)

    def test_c_to_sac(self):
        pass


class TestSacToC(unittest.TestCase):
    def setUp(self):
        pass

    def test_sac_to_c(self):
        self.assertEqual(saclib.sac_to_c("foo()", []), "SACf__MAIN__foo")
        self.assertEqual(saclib.sac_to_c("foo::bar(int[], int)", []), "SACf__FOO__bar__i_i__i")

        input_vars = "SACp_emal_5_x\nSACp_emal_5_x__SSA01\nSACl_foo\nSACf__MAIN__foo"
        self.assertEqual(saclib.sac_to_c("x", input_vars), "SACp_emal_5_x__SSA01")

        input_vars = "SACp_emal_5_x\nSACl_foo\nSACf__MAIN__foo"
        self.assertEqual(saclib.sac_to_c("x", input_vars), "SACp_emal_5_x")


class TestSacinfoCommand(unittest.TestCase):
    def setUp(self):
        pass


class TestCommandConversion(unittest.TestCase):
    def setUp(self):
        pass

    def test_extract_sacblocks(self):
        # Test for a sacblock containing a variable identifier
        input_text = "watchpoint *sac(foo)"
        output = saclib.extract_sacblocks(input_text)
        self.assertEqual(output[0][0], 11)
        self.assertEqual(output[0][1], 19)
        self.assertEqual(output[0][2], "foo")

        # Test for two sacblocks
        input_text = "breakpoint *sac(foo) *sac(bar)"
        output = saclib.extract_sacblocks(input_text)
        self.assertEqual(output[0][0], 11)
        self.assertEqual(output[0][1], 19)
        self.assertEqual(output[0][2], "foo")
        self.assertEqual(output[1][0], 21)
        self.assertEqual(output[1][1], 29)
        self.assertEqual(output[1][2], "bar")

        # Test for a sacblock containing a function
        input_text = "breakpoint *sac(foo())"
        output = saclib.extract_sacblocks(input_text)
        self.assertEqual(output[0][0], 11)
        self.assertEqual(output[0][1], 21)
        self.assertEqual(output[0][2], "foo()")

        # Test for a function with arguments
        input_text = "breakpoint *sac(foo(int, float, int[]))"
        output = saclib.extract_sacblocks(input_text)
        self.assertEqual(output[0][0], 11)
        self.assertEqual(output[0][1], 38)
        self.assertEqual(output[0][2], "foo(int, float, int[])")

    def test_replace_sacblocks(self):
        input_vars = "SACp_emal_5_x\nSACp_emal_5_x__SSA01\nSACl_foo\nSACf__MAIN__foo"

        input_text = "breakpoint *sac(foo(int, float, int[]))"
        output = saclib.extract_sacblocks(input_text)
        self.assertEqual(saclib.replace_sacblocks(input_text, output, input_vars),
                         "breakpoint SACf__MAIN__foo__i__f__i_i")

        input_text = "breakpoint *sac(foo(int, float, int[])) *sac(x)"
        output = saclib.extract_sacblocks(input_text)
        self.assertEqual(saclib.replace_sacblocks(input_text, output, input_vars),
                         "breakpoint SACf__MAIN__foo__i__f__i_i SACp_emal_5_x__SSA01")

        input_text = "watchpoint *sac(x))"
        output = saclib.extract_sacblocks(input_text)
        self.assertEqual(saclib.replace_sacblocks(input_text, output, input_vars),
                         "watchpoint SACp_emal_5_x__SSA01")

        input_vars = "SACp_emal_5_x\nSACl_foo\nSACf__MAIN__foo"
        input_text = "watchpoint *sac(x))"
        output = saclib.extract_sacblocks(input_text)
        self.assertEqual(saclib.replace_sacblocks(input_text, output, input_vars),
                         "watchpoint SACp_emal_5_x")


if __name__ == '__main__':
    unittest.main()