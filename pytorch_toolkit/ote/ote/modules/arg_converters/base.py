"""
 Copyright (c) 2020 Intel Corporation

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
"""

import os
from abc import ABCMeta, abstractmethod
from collections import namedtuple

def _debug_print_converted_args_and_exit(converted_args):
    from pprint import pformat
    s = pformat(converted_args)
    s = '\nconverted_args=\n' + s + '\n'
    s = '\n====== '.join(s.split('\n'))
    print(s, flush=True)
    raise RuntimeError('_debug_print_converted_args_and_exit')

def map_args(src_args, args_map):
    return {v: src_args[k] for k, v in args_map.items()}

class ArgConverterMaps(metaclass=ABCMeta):
    @abstractmethod
    def train_update_args_map(self):
        """
        Returns a map:
            from: the name of cmd line arguments of the corresponding **train** argparser.parse_args
                  (e.g. `argparser = DefaultArgParser.get_train_parser()`)
            to:   the fields of mmdetection/mmaction/other config for its **train** script in the form
                  compatible with mmcv.Config.merge_from_dict
        """
        pass

    @abstractmethod
    def test_update_args_map(self):
        """
        Returns a map:
            from: the name of cmd line arguments of the corresponding **test** argparser.parse_args
                  (e.g. `argparser = DefaultArgParser.get_test_parser()`)
            to:   the fields of mmdetection/mmaction/other config for its **test** script in the form
                  compatible with mmcv.Config.merge_from_dict
        """
        pass

    @abstractmethod
    def compress_update_args_map(self):
        """
        Returns a map:
            from: the name of cmd line arguments of the corresponding **compress** argparser.parse_args
                  (e.g. `argparser = DefaultArgParser.get_compression_parser()`)
            to:   the fields of mmdetection/mmaction/other config for its **train** script in the form
                  compatible with mmcv.Config.merge_from_dict to makes compression
                  (note that compression makes the original train script with special tuned config;
                   typically the parameters are the same as for training except
                   learning rate and total_epochs parameters)

        """
        pass

    @abstractmethod
    def train_out_args_map(self):
        """
        Returns a map:
            from: the name of cmd line arguments of the corresponding **train** argparser.parse_args
            to:   the names of additional parameters of the `__call__` method of the corresponding ote trainer class
                  (e.g. MMDetectionTrainer) in the form suitable for `trainer_class(**kwargs)`
        """
        return {
                'gpu_num': 'gpu_num',
                'tensorboard_dir': 'tensorboard_dir'
               }
    @abstractmethod
    def compress_out_args_map(self):
        """
        Returns a map:
            from: the name of cmd line arguments of the corresponding **compress** argparser.parse_args
            to:   the names of additional parameters of the `__call__` method of the corresponding
                  ote trainer class (e.g. MMDetectionTrainer) in the form suitable
                  for call `trainer_class(**kwargs)`
                  (note that compression make the same trainer class as training, but with tuned
                  config file)
        """
        return {
                'gpu_num': 'gpu_num',
                'tensorboard_dir': 'tensorboard_dir'
               }
    @abstractmethod
    def test_out_args_map(self):
        """
        Returns a map:
            from: the name of cmd line arguments of the corresponding **test** argparser.parse_args
            to:   the names of additional parameters of the `__call__` method of the corresponding ote
                  evaluator class (e.g. MMDetectionEvaluator) in the form suitable for
                  call `evaluator_class(**kwargs)`
        """
        return {
                'load_weights': 'snapshot',
                'save_metrics_to': 'out',
                'save_output_to': 'show_dir'
               }

    @abstractmethod
    def get_extra_train_args(self, args):
        """ Gets from the parsed output of the corresponding ote train argparser.parse_args
            (e.g. `argparser = DefaultArgParser.get_train_parser()`)
            additional changes that should be applied to mmdetection/mmation/other training config file,
            the changes will be in the form compatible with mmcv.Config.merge_from_dict
        """
        return {}

    @abstractmethod
    def get_extra_test_args(self, args):
        """ Gets from the parsed output of the corresponding ote train argparser.parse_args
            (e.g. `argparser = DefaultArgParser.get_train_parser()`)
            additional changes that should be applied to mmdetection/mmation/other testing config file,
            the changes will be in the form compatible with mmcv.Config.merge_from_dict
        """
        return {}

HooksForAction = namedtuple('HooksForAction',
                            ['update_args_map_hook', 'get_extra_args_hook', 'out_args_map_hook'])

class GroupHooksForActions:
    @staticmethod
    def get_hooks_for_train(arg_conv_maps):
        return HooksForAction(update_args_map_hook=arg_conv_maps.train_update_args_map,
                              get_extra_args_hook=arg_conv_maps.get_extra_train_args,
                              out_args_map_hook=arg_conv_maps.train_out_args_map)

    @staticmethod
    def get_hooks_for_test(arg_conv_maps):
        return HooksForAction(update_args_map_hook=arg_conv_maps.test_update_args_map,
                              get_extra_args_hook=arg_conv_maps.get_extra_test_args,
                              out_args_map_hook=arg_conv_maps.test_out_args_map)

    @staticmethod
    def get_hooks_for_compress(arg_conv_maps):
        return HooksForAction(update_args_map_hook=arg_conv_maps.compress_update_args_map,
                              get_extra_args_hook=arg_conv_maps.get_extra_train_args,
                              out_args_map_hook=arg_conv_maps.compress_out_args_map)


class BaseArgConverterOLD(metaclass=ABCMeta):
    train_update_args_map = {}
    test_update_args_map = {}
    compress_update_args_map = {}
    train_to_compress_update_args_map = {}
    # TODO(LeonidBeynenson): replace dicts train_update_args_map, test_update_args_map,
    #       and compress_update_args_map with call of a special function
    #       that may be passed to constructor of the class as a
    #       parameter.
    #       This will allow to avoid copying between these dicts.

    train_out_args_map = {
        'gpu_num': 'gpu_num',
        'tensorboard_dir': 'tensorboard_dir'
    }
    compress_out_args_map = {
        'gpu_num': 'gpu_num',
        'tensorboard_dir': 'tensorboard_dir',
        'nncf_quantization': 'nncf_quantization',
        'nncf_pruning': 'nncf_pruning',
        'nncf_sparsity': 'nncf_sparsity',
        'nncf_binarization': 'nncf_binarization',
    }
    test_out_args_map = {
        'load_weights': 'snapshot',
        'save_metrics_to': 'out',
        'save_output_to': 'show_dir',
    }

    def __init__(self):
        pass

    def convert_train_args(self, model_template_path, args):
        update_args = self.__map_args(args, self.train_update_args_map)

        extra_args = self._get_extra_train_args(args)
        update_args.update(extra_args)

        template_folder = os.path.dirname(model_template_path)
        converted_args = {
            'config': os.path.join(template_folder, args['config']),
            'out': os.path.join(args['save_checkpoints_to'], model_template_path),
            'update_config': update_args,
        }
        converted_args.update(self.__map_args(args, self.train_out_args_map))

        _debug_print_converted_args_and_exit(converted_args)
        return converted_args

    def convert_compress_args(self, model_template_path, args):
        update_args = self.__map_args(args, self.compress_update_args_map)

        # TODO(LeonidBeynenson): think on _get_extra_compress_args
        #       Now _get_extra_train_args is used since it's the same
        extra_args = self._get_extra_train_args(args)
        update_args.update(extra_args)

        template_folder = os.path.dirname(model_template_path)
        converted_args = {
            'config': os.path.join(template_folder, args['config']),
            'out': os.path.join(args['save_checkpoints_to'], model_template_path),
            'update_config': update_args,
        }
        converted_args.update(self.__map_args(args, self.compress_out_args_map))

        _debug_print_converted_args_and_exit(converted_args)
        return converted_args

    def convert_test_args(self, model_template_path, args):
        update_args = self.__map_args(args, self.test_update_args_map)

        extra_args = self._get_extra_test_args(args)
        update_args.update(extra_args)

        template_folder = os.path.dirname(model_template_path)
        converted_args = {
            'config': os.path.join(template_folder, args['config']),
            'update_config': update_args,
        }
        converted_args.update(self.__map_args(args, self.test_out_args_map))

        _debug_print_converted_args_and_exit(converted_args)
        return converted_args

    def _get_extra_train_args(self, args):
        return {}

    def _get_extra_test_args(self, args):
        return {}

    @staticmethod
    def __map_args(src_args, args_map):
        return {v: src_args[k] for k, v in args_map.items()}

class BaseArgConverter:
    def __init__(self, arg_conv_maps):
        assert isinstance(arg_conv_maps, ArgConverterMaps)
        self.arg_conv_maps = arg_conv_maps

    @staticmethod
    def _convert_args_by_hooks_for_action(hooks_for_action, model_template_path, args):
        assert isinstance(hooks_for_action, HooksForAction)

        update_args_map = hooks_for_action.update_args_map_hook()
        update_args = map_args(args, update_args_map)

        extra_args = hooks_for_action.get_extra_args_hook(args)
        update_args.update(extra_args)

        template_folder = os.path.dirname(model_template_path)
        converted_args = {
            'config': os.path.join(template_folder, args['config']),
            'update_config': update_args,
        }
        if args.get('save_checkpoints_to'):
            converted_args['out'] = os.path.join(args['save_checkpoints_to'], model_template_path)

        additional_converted_args_map = hooks_for_action.out_args_map_hook()
        additional_converted_args = map_args(args, additional_converted_args_map)
        converted_args.update(additional_converted_args)

        _debug_print_converted_args_and_exit(converted_args)
        return converted_args

    def convert_train_args(self, model_template_path, args):
        hooks_for_action = GroupHooksForActions.get_hooks_for_train(self.arg_conv_maps)
        return self._convert_args_by_hooks_for_action(hooks_for_action, model_template_path, args)

    def convert_compress_args(self, model_template_path, args):
        hooks_for_action = GroupHooksForActions.get_hooks_for_compress(self.arg_conv_maps)
        return self._convert_args_by_hooks_for_action(hooks_for_action, model_template_path, args)

    def convert_test_args(self, model_template_path, args):
        hooks_for_action = GroupHooksForActions.get_hooks_for_test(self.arg_conv_maps)
        return self._convert_args_by_hooks_for_action(hooks_for_action, model_template_path, args)
