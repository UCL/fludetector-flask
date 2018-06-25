from enum import Enum
import matlab.engine
import tempfile


def buildMatlab(matlabType):
    if matlabType is MatlabType.LOCAL:
        return LocalMatlab()
    if matlabType is MatlabType.REMOTE:
        return RemoteMatlab()


class MatlabType(Enum):
    LOCAL, REMOTE, LEGACY = range(3)


class LocalMatlab(object):

    def __init__(self):
        self.conf = MatlabType.LOCAL
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


class RemoteMatlab(object):
    pass
