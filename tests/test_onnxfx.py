import unittest
import numpy as np
import onnxruntime as _ort
from onnxconverter_common.onnx_fx import Graph
from onnxconverter_common.onnx_fx import GraphFunctionType as _Ty


def _ort_inference(mdl, inputs):
    sess = _ort.InferenceSession(mdl.SerializeToString())
    return sess.run(None, inputs)


Graph.inference_runtime = _ort_inference
Graph.opset = 9
onnx_function = Graph.trace


class ONNXFunctionTest(unittest.TestCase):
    # this works, and the exported graph is usable:
    def test_core(self):
        @onnx_function
        def f(x, y):
            return x + y

        @onnx_function
        def g(x, y):
            return x.ox.abs(f(x, y) + 1.0)

        g.save('test_g.onnx')
        self.assertTrue(
            np.allclose(g([2.0], [-5.0]), np.array([2.0])))

    def test_loop(self):
        @onnx_function(outputs=['y1', 'y2', 'y3', 'y4'],
                     input_types=[_Ty.I(shape=[1])],
                     output_types=[_Ty.F(shape=[None]), _Ty.F(shape=[None]), _Ty.F(shape=[None]), _Ty.F(shape=[None])])
        def loop_test(len):
            ox = len.ox
            s_len = ox.squeeze(len, axes=[0])
            is_true = ox.constant(value=True)

            @onnx_function(outputs=['c_o', 'i_o', 'j_o', 'all_i', 'all_j'],
                         output_types=[_Ty.b, _Ty.f, _Ty.f, _Ty.f, _Ty.f],
                         input_types=[_Ty.I([1]), _Ty.b, _Ty.F(shape=[1]), _Ty.F(shape=[1])])
            def range_body(iter_n, cond, i, j):
                return (is_true,
                        i + i.ox.constant(value=1.0), j + 2.0, i, j)

            one_c = ox.constant(value=-1.0)
            y1, y2, y3, y4 = ox.loop(s_len, is_true, range_body, inputs=[one_c, one_c],
                                     outputs=['y1_o', 'y2_o', 'y3_o', 'y4_o'])
            return y1, y2, y3, y4

        self.assertEqual(
            loop_test(np.array([16], dtype=np.int64))[2][4], 3.0)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(ONNXFunctionTest)
    #suite.debug()
    unittest.TextTestRunner().run(suite)