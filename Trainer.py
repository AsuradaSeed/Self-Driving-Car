import tensorflow as tf
from util import mkdir_tfboard_run_dir,mkdir,shell_command
from data_augmentation import process_data
import os
from Dataset import Dataset
import argparse


class Trainer:

    def __init__(self, data_path, model_file, epochs=50, max_sample_records=500):
        self.model_file = model_file
        self.data_path = data_path
        self.epochs = int(epochs)
        self.max_sample_records = max_sample_records
        self.tfboard_basedir = os.path.join(self.data_path, 'tf_visual_data', 'runs')
        self.tfboard_run_dir = mkdir_tfboard_run_dir(self.tfboard_basedir)
        self.results_file = os.path.join(self.tfboard_run_dir, 'results.txt')
        model_checkpoint_path = os.path.join(self.tfboard_run_dir,'trained_model')

    # Assumes all models have these same inputs
    def train(self, sess, x, y_, accuracy, train_step, train_feed_dict, test_feed_dict):

        # To view graph: tensorboard --logdir=/Users/ryanzotti/Documents/repos/Self_Driving_RC_Car/tf_visual_data/runs
        tf.summary.scalar('accuracy', accuracy)
        merged = tf.summary.merge_all()

        # Archive this script to document model design in event of good results that need to be replicated
        model_file_path = os.path.dirname(os.path.realpath(__file__)) + '/' + os.path.basename(__file__)
        cmd = 'cp {model_file} {archive_path}'
        shell_command(cmd.format(model_file=self.model_file, archive_path=self.tfboard_run_dir + '/'))

        sess.run(tf.global_variables_initializer())

        dataset = Dataset(input_file_path=self.data_path, max_sample_records=self.max_sample_records)

        # Not sure what these two lines do
        run_opts = tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE)
        run_opts_metadata = tf.RunMetadata()

        train_images, train_labels = process_data(dataset.get_sample(train=True))
        train_feed_dict[x] = train_images
        train_feed_dict[y_] = train_labels
        train_summary, train_accuracy = sess.run([merged, accuracy], feed_dict=train_feed_dict,
                                                 options=run_opts, run_metadata=run_opts_metadata)
        test_images, test_labels = process_data(dataset.get_sample(train=False))
        test_feed_dict[x] = test_images
        test_feed_dict[y_] = test_labels
        test_summary, test_accuracy = sess.run([merged, accuracy], feed_dict=test_feed_dict,
                                               options=run_opts, run_metadata=run_opts_metadata)
        message = "epoch: {0}, training accuracy: {1}, validation accuracy: {2}"
        print(message.format(-1, train_accuracy, test_accuracy))

        with open(self.results_file,'a') as f:
            f.write(message.format(-1, train_accuracy, test_accuracy)+'\n')

        train_batches = dataset.get_batches(train=True)
        batch = train_batches[0]
        images, labels = process_data(batch)
        train_feed_dict[x] = images
        train_feed_dict[y_] = labels
        for epoch in range(self.epochs):
            train_step.run(feed_dict=train_feed_dict)

            # TODO: remove all this hideous boilerplate
            run_opts = tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE)
            run_opts_metadata = tf.RunMetadata()
            train_summary, train_accuracy = sess.run([merged, accuracy], feed_dict=train_feed_dict,
                                                     options=run_opts, run_metadata=run_opts_metadata)
            test_images, test_labels = process_data(dataset.get_sample(train=False))
            test_feed_dict[x] = test_images
            test_feed_dict[y_] = test_labels
            test_summary, test_accuracy = sess.run([merged, accuracy], feed_dict=train_feed_dict,
                                                   options=run_opts, run_metadata=run_opts_metadata)
            print(message.format(epoch, train_accuracy, test_accuracy))
            with open(self.results_file, 'a') as f:
                f.write(message.format(epoch, train_accuracy, test_accuracy)+'\n')

        # Save the trained model to a file
        saver = tf.train.Saver()
        save_path = saver.save(sess, self.tfboard_run_dir + "/model.ckpt")

        # Marks unambiguous successful completion to prevent deletion by cleanup script
        shell_command('touch ' + self.tfboard_run_dir + '/SUCCESS')


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("-d", "--datapath", required=False,
                    help="path to all of the data",
                    default='/Users/ryanzotti/Documents/repos/Self_Driving_RC_Car/data')
    ap.add_argument("-e", "--epochs", required=False,
                    help="quantity of batch iterations to run",
                    default='50')
    args = vars(ap.parse_args())
    data_path = args["datapath"]
    epochs = args["epochs"]
    return data_path, epochs