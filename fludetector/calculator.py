from enum import Enum
import tempfile


def buildCalculator(calculatorType):
    if calculatorType is CalculatorType.MATLAB:
        return LocalMatlab()
    if calculatorType is CalculatorType.REMOTE:
        return RemoteCalculator()
    if calculatorType is CalculatorType.OCTAVE:
        return LocalOctave()


class CalculatorType(Enum):
    MATLAB, REMOTE, LEGACY, OCTAVE = range(4)


class LocalMatlab(object):

    def __init__(self):
        import matlab.engine
        self.conf = CalculatorType.MATLAB
        self.engine = matlab.engine.start_matlab("-nodisplay -nojvm")
        self.engine.cd("matlab")
        self.engine.run("gpml/startup.m", nargout=0)

    def __del__(self):
        self.engine.quit()

    def calculateModelScore(self, model, averages):
        fhin = tempfile.NamedTemporaryFile(prefix='fludetector-matlab-input.')
        fhout = tempfile.NamedTemporaryFile(prefix='fludetector-matlab-output.')
        fhin.write('\n'.join('%s,%f' % a for a in averages))
        fhin.flush()
        self.engine.evalc("fin = '%s'" % fhin.name, nargout=0)
        self.engine.evalc("fout = '%s'" % fhout.name, nargout=0)
        self.engine.run("%s(fin,fout)" % model.get_data()['matlab_function'], nargout=0)
        value = float(open(fhout.name).read().strip())
        fhin.close()
        fhout.close()
        return value


class RemoteCalculator(object):
    pass


class LocalOctave(object):

    def __init__(self):
        self.conf = CalculatorType.OCTAVE
        from oct2py import octave
        self.engine = octave
        self.engine.cd("octave")
        self.engine.run("gpml/startup.m")

    def calculateModelScore(self, model, averages):
        fhin = tempfile.NamedTemporaryFile(prefix='fludetector-matlab-input.')
        fhout = tempfile.NamedTemporaryFile(prefix='fludetector-matlab-output.')
        fhin.write('\n'.join('%s,%f' % a for a in averages))
        fhin.flush()
        self.engine.eval("%s('%s','%s')" % (model.get_data()['matlab_function'], fhin.name, fhout.name))
        value = float(open(fhout.name).read().strip())
        fhin.close()
        fhout.close()
        return value
