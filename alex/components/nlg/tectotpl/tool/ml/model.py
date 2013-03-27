#!/usr/bin/env python
# coding=utf-8
#
#
from __future__ import unicode_literals
import os


"""\
Classification models using scikit-learn. The main objects here are Model
and SplitModel.
"""

from treex.core.util import file_stream
from treex.core.log import log_info
from sklearn.metrics import zero_one_score
from treex.tool.ml.dataset import DataSet
from sklearn.dummy import DummyClassifier
from treex.core.exception import RuntimeException
from treex.tool.cluster import Job
import numpy as np
import pickle
import marshal
import re
import types
import codecs
import sys

__author__ = "Ondřej Dušek"
__date__ = "2012"


class AbstractModel(object):
    """\
    Abstract ancestor of different model classes
    """

    def __init__(self, config):
        """\
        Initialize a few attributes from the configuration.
        """
        # this will store the training data headers for value ordering
        self.data_headers = None
        # attribute pre-selection (remove class attribute from select_attr)
        self.class_attr = config['class_attr']
        self.select_attr = config.get('select_attr', [])
        if self.class_attr in self.select_attr:
            self.select_attr.remove(self.class_attr)
        # part of the training data to be used
        self.train_part = config.get('train_part', 1)

    def evaluate(self, test_file, encoding='UTF-8', classif_file=None):
        """\
        Evaluate on the given test data file. Return accuracy.
        If classif_file is set, save the classification results to this file.
        """
        test = DataSet()
        test.load_from_arff(test_file, encoding)
        values = self.classify(test)
        golden = self.get_classes(test, dtype=None)
        if classif_file is not None:
            classif = DataSet()
            classif.load_from_vect(test.get_attrib(self.class_attr), values)
            classif.rename_attrib(self.class_attr, self.PREDICTED)
            test.merge(classif)
            test.save_to_arff(classif_file, encoding)
        return zero_one_score(golden, values)

    @staticmethod
    def load_from_file(model_file):
        """\
        Load the model from a pickle file or stream
        (supports GZip compression).
        """
        log_info('Loading model from file ' + str(model_file))
        fh = file_stream(model_file, mode='rb', encoding=None)
        unpickler = pickle.Unpickler(fh)
        model = unpickler.load()
        fh.close()
        log_info('Model loaded successfully.')
        return model

    def load_training_set(self, filename, encoding='UTF-8'):
        """\
        Load the given training data set into memory and strip it if
        configured to via the train_part parameter.
        """
        log_info('Loading training data set from ' + str(filename) + '...')
        train = DataSet()
        train.load_from_arff(filename, encoding)
        if self.train_part < 1:
            train = train.subset(0, int(round(self.train_part * len(train))),
                                 copy=False)
        return train

    def save_to_file(self, model_file):
        """\
        Save the model to a pickle file or stream (supports GZip compression).
        """
        log_info('Saving model to file ' + str(model_file))
        fh = file_stream(model_file, mode='wb', encoding=None)
        pickle.Pickler(fh, pickle.HIGHEST_PROTOCOL).dump(self)
        fh.close()
        log_info('Model successfully saved.')

    def get_classes(self, data, dtype=int):
        """\
        Return a vector of class values from the given DataSet.
        If dtype is int, the integer values are returned. If dtype is
        None, the string values are returned.
        """
        return np.array(data.attrib_as_vect(self.class_attr, dtype=dtype))

    def classify(self, instances):
        """\
        This must be implemented in derived classes.
        """
        raise NotImplementedError()

    def check_classification_input(self, instances):
        """\
        Check classification input data format, convert to list if needed.
        """
        # empty list check
        if not instances:
            return instances, False
        # treat single values as one-member lists
        nolist = False
        if not isinstance(instances, list) and \
                not isinstance(instances, DataSet):
            nolist = True
            instances = [instances]
        return instances, nolist


class Model(AbstractModel):

    # predicted class name
    PREDICTED = 'PREDICTED'

    def __init__(self, config):
        """\
        Initialize the model with the given configuration.
        """
        super(Model, self).__init__(config)
        # vectorization and filtering settings
        self.filter_attr = config.get('filter_attr')
        self.vectorizer = config.get('vectorizer')
        self.vectorizer_trained = False
        self.feature_filter = config.get('feature_filter')
        self.feature_filter_trained = False
        self.use_weights = config.get('use_weights', False)
        # classification settings
        self.classifier = self.construct_classifier(config)
        self.classifier_trained = False
        self.postprocess = config.get('postprocess')

    def construct_classifier(self, cfg):
        """\
        Given the config file, construct the classifier (based on the
        'classifier' or 'classifier_class'/'classifier_params' settings.
        Defaults to DummyClassifier.
        """
        if 'classifier' in cfg:
            return cfg['classifier']
        elif 'classifier_class' in cfg:
            if 'classifier_params' in cfg:
                return cfg['classifier_class'](**cfg['classifier_params'])
            else:
                return cfg['classifier_class']()
        else:
            return DummyClassifier()

    @staticmethod
    def create_training_job(config, work_dir, train_file,
                            name=None, memory=8, encoding='UTF-8'):
        """\
        Submit a training process on the cluster which will save the
        model to a pickle. Return the submitted job and the future location of
        the model pickle.
        train_file cannot be a stream, it must be an actual file.
        """
        # purge name
        if name is None:
            name = 'TR-' + re.sub(r'[^A-Za-z0-9_]', '_', train_file)
        else:
            name = re.sub(r'[^A-Za-z0-9_]', '_', name)
        # create working directory, if not existing
        if not os.path.isdir(work_dir):
            os.mkdir(work_dir)
        train_file = os.path.abspath(train_file)
        # generate model file name
        model_file = os.path.abspath(os.path.join(work_dir,
                                                  name + '-model.pickle.gz'))
        config_pickle = os.path.abspath(os.path.join(work_dir,
                                                     name + '-cfg.pickle.gz'))
        # create the configuration pickle
        fh = file_stream(config_pickle, mode='wb', encoding=None)
        pickle.Pickler(fh, pickle.HIGHEST_PROTOCOL).dump(config)
        fh.close()
        # create the job
        job = Job(name=name, work_dir=work_dir)
        job.code = "fh = file_stream('" + config_pickle + \
                "', mode='rb', encoding=None)\n" + \
                "cfg = pickle.Unpickler(fh).load()\n" + \
                "fh.close()\n" + \
                "model = Model(cfg)\n" + \
                "model.train('" + train_file + "', encoding='" + \
                encoding + "')\n" \
                "model.save_to_file('" + model_file + "')\n"
        job.header += "from treex.tool.ml.model import Model\n" + \
                "import pickle\n" + \
                "from treex.core.util import file_stream\n"
        return job, model_file

    def train_on_data(self, train):
        """\
        Train model on the specified training data set (which must be a loaded
        DataSet object).
        """
        log_info('Preparing data set...')
        self.data_headers = train.get_headers()
        train_vect = self.__vectorize(train)
        train_classes = self.get_classes(train)
        # if all the training data have the same class, use a dummy classifier
        if train.get_attrib(self.class_attr).num_values == 1:
            self.feature_filter = None
            self.classifier = DummyClassifier()
        # filter features
        log_info('Filtering...')
        train_filt = self.__filter_features(train_vect, train_classes)
        # train the classifier
        log_info('Training...')
        if self.use_weights:
            self.classifier.fit(train_filt, train_classes,
                                sample_weight=train.inst_weights)
        else:
            self.classifier.fit(train_filt, train_classes)
        self.classifier_trained = True
        log_info('Training done.')

    def train(self, train_file, encoding='UTF-8'):
        """\
        Train the model on the specified training data file.
        """
        self.train_on_data(self.load_training_set(train_file, encoding))

    def classify(self, instances):
        """\
        Classify a set of instances (possibly one member).
        """
        # prepare for classification
        instances, nolist = self.check_classification_input(instances)
        if not instances:
            return instances
        # vectorize and filter the instances
        inst_vect = self.__vectorize(instances)
        if self.feature_filter is not None:
            inst_filt = self.__filter_features(inst_vect)
        else:
            inst_filt = inst_vect
        # classify
        values = self.classifier.predict(inst_filt)
        # return the result
        class_attr = self.data_headers.get_attrib(self.class_attr)
        values = [class_attr.value(val) for val in values]
        # (optional) post-processing
        if self.postprocess:
            values = [self.postprocess(inst, val)
                      for inst, val in zip(instances, values)]
        if nolist:
            return values[0]
        return values

    def __vectorize(self, data):
        """\
        Train vectorization and subsequently vectorize. Accepts a DataSet
        or a list of dictionaries to be vectorized.
        """
        # no vectorization performed, only converted to matrix
        if self.vectorizer is None:
            if not isinstance(data, DataSet):
                data_set = DataSet()
                data_set.load_from_dict(data)
                data = data_set
            data.match_headers(self.data_headers, add_values=True)
            # TODO pre-filtering here?
            return data.as_bunch(target=self.class_attr,
                                 select_attrib=self.select_attr).data
        # vectorization needed: converted to dictionary
        # and passed to the vectorizer
        if isinstance(data, DataSet):
            data = data.as_dict(select_attrib=self.select_attr,
                                mask_attrib=self.class_attr)
        else:
            data = [{key: val for key, val in inst.items()
                     if key != self.class_attr and key in self.select_attr}
                    for inst in data]
        # pre-filter attributes if filter_attr is set
        if self.filter_attr:
            data = [{key: val for key, val in inst.items()
                     if self.filter_attr(key, val)} for inst in data]
        if not self.vectorizer_trained:
            self.vectorizer.fit(data)
            self.vectorizer_trained = True
        return self.vectorizer.transform(data).tocsr()

    def __filter_features(self, data, classes=None):
        """\
        Filter features according to the pre-selected filter. Return the
        same set of features if the filter is not set.
        """
        if self.feature_filter is None:
            return data
        if not self.feature_filter_trained:
            if classes is None:
                raise RuntimeException('Classes must be given to ' +
                                       'train a feature filter!')
            self.feature_filter.fit(data, classes)
            self.feature_filter_trained = True
        return self.feature_filter.transform(data)

    def __marshal_member(self, state, key):
        """\
        Check for a key lambda function under the specified key
        and marshal it if needed.
        """
        if key in state and hasattr(state[key], '__call__'):
            try:
                code = state[key].func_code
                state[key] = marshal.dumps(code)
            except (AttributeError, ValueError):
                # try to use original version if marshaling fails
                pass

    def __demarshal_member(self, state, key):
        """\
        Check for a key lambda function under the specified key
        and de-marshal it if needed.
        """
        if key in state:
            try:
                code = marshal.loads(state[key])
                state[key] = types.FunctionType(code, globals())
            except (TypeError, ValueError):
                # try to use original version if demarshaling fails
                pass

    def __getstate__(self):
        """\
        Check and marshal member lambda functions.
        """
        state = self.__dict__
        self.__marshal_member(state, 'filter_attr')
        self.__marshal_member(state, 'postprocess')
        return state

    def __setstate__(self, state):
        """\
        Check and de-marshal member lambda functions.
        """
        self.__demarshal_member(state, 'filter_attr')
        self.__demarshal_member(state, 'postprocess')
        if 'postprocess' not in state:
            state['postprocess'] = None
        self.__dict__ = state


class SplitModel(AbstractModel):
    """\
    A model that's actually composed of several Model-s.
    """

    def __init__(self, config):
        """\
        Just store the configuration, be prepared for training.
        """
        super(SplitModel, self).__init__(config)
        # create storage for split models
        self.divide_func = config['divide_func']
        self.config = config
        self.models = {}
        self.backoff_model = None
        self.trained = False

    def train(self, train_file, work_dir, memory=8, encoding='UTF-8'):
        """\
        Read training data, split them and train the individual models
        (in cluster jobs).
        """
        # load the entire data set
        train = self.load_training_set(train_file, encoding)
        self.data_headers = train.get_headers()
        # train a backoff model
        log_info('Training a backoff model...')
        self.backoff_model = self.__train_backoff_model(train)
        # split it
        log_info('Split...')
        train_split = train.split(eval(self.divide_func), keep_copy=False)
        jobs = []
        model_files = {}
        # save training files and create training jobs
        for key, subset in train_split.iteritems():
            fn = re.sub(r'(.arff(.gz)?)?$', '-' + key + '.arff.gz', train_file)
            fn = os.path.join(work_dir, os.path.basename(fn))
            subset.save_to_arff(fn, encoding)
            job, model_file = Model.create_training_job(self.config, work_dir,
                                                        fn, memory=memory,
                                                        encoding=encoding)
            jobs.append(job)
            model_files[key] = model_file
        # submit the training jobs and wait for all of them
        log_info('Submitting training jobs...')
        for job in jobs:
            job.submit()
        log_info('Waiting for jobs...')
        for job in jobs:
            job.wait()
        # load all models
        log_info('Training complete. Assembling model files...')
        for key, model_file in model_files.iteritems():
            self.models[key] = Model.load_from_file(model_file)
        self.trained = True
        log_info('Training done.')

    def classify(self, instances):
        """\
        Classify a set of instances.
        """
        # prepare for classification
        instances, nolist = self.check_classification_input(instances)
        if not instances:
            return instances
        # classify each instance with the respective model
        # TODO: bulk classify
        results = []
        divide_func = eval(self.divide_func)
        for instance in instances:
            model_key = divide_func(0, instance)
            if model_key in self.models:
                results.append(self.models[model_key].classify(instance))
            else:
                results.append(self.backoff_model.classify(instance))
        # return the results
        if nolist:
            return results[0]
        return results

    def __train_backoff_model(self, train):
        """\
        Train a DummyClassifier back-off on the given training data.
        """
        config = {'class_attr': self.class_attr, 'select_attr': []}
        model = Model(config)
        model.train_on_data(train)
        return model
