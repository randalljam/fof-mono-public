Speech Classification From Scratch
https://speechbrain.readthedocs.io/en/latest/tutorials/tasks/speech-classification-from-scratch.html

Do you want to figure out how to implement a classification system with SpeechBrain? Look no further, you’re in the right place. This tutorial will walk you through all the steps needed to implement an utterance-level classifier in SpeechBrain.
The tutorial will initially focus on speaker identification and will describe, along the way, how to extend it to many other classification tasks such as language-id, emotion recognition, sound classification, keyword spotting, and many others.

Models

Many neural models can be used to approach this kind of task. In this tutorial, we will focus on a TDNN classifier (xvector) and a very recent model called ECAPA-TDNN that showed impressive performance in speaker verification and diarization.

Data

Training will be done with a small open-source dataset called mini-librispeech, which only contains few hours of training data. In a real case, you need a much larger dataset. For some examples on a real task, please take a look into our Voxceleb recipes.

Code

In this tutorial, we will refer to the code in speechbrain/templates/speaker_id.

Installation

Before starting, let’s install speechbrain:

%%capture

# Installing SpeechBrain via pip
BRANCH = 'develop'
!python -m pip install git+https://github.com/speechbrain/speechbrain.git@$BRANCH

# Clone SpeechBrain repository (development branch)
!git clone https://github.com/speechbrain/speechbrain/
%cd /content/speechbrain/

Which steps are needed?

Training an utterance-level classifier is relatively easy in SpeechBrain. The steps to follows are:

Prepare your data. The goal of this step is to create the data manifest files (in CSV or JSON format). The data manifest files tell SpeechBrain where to find the speech data and their corresponding utterance-level classification (e.g., speaker id). In this tutorial, the data manifest files are created by mini_librispeech_prepare.py.
Train the classifier. At this point, we are ready to train our classifier. To train a speaker-id classifier based on TDNN + statistical pooling (xvectors), run the following command:
cd speechbrain/templates/speaker_id/
python train.py train.yaml

Later, we will describe how to plug another model called Emphasized Channel Attention, Propagation, and Aggregation model (ECAPA) that turned out to provide impressive performance in speaker recognition tasks.

Use the classifier (inference): After training, we can use the classifier for inference. A class called EncoderClassifier is designed to make inference easier. We also designed a class called SpeakerRecognition to make inference on a speaker verification task easier.
We will now provide a detailed description of all these steps.

Step 1: Prepare your data

The goal of data preparation is to create the data manifest files. These files tell SpeechBrain where to find the audio data and their corresponding utterance-level classification. They are text files written in the popular CSV and JSON formats.

Data manifest files

Let’s take a look into how a data manifest file in JSON format looks like:

{
  "163-122947-0045": {
    "wav": "{data_root}/LibriSpeech/train-clean-5/163/122947/163-122947-0045.flac",
    "length": 14.335,
    "spk_id": "163"
  },
  "7312-92432-0025": {
    "wav": "{data_root}/LibriSpeech/train-clean-5/7312/92432/7312-92432-0025.flac",
    "length": 12.01,
    "spk_id": "7312"
  },
  "7859-102519-0036": {
    "wav": "{data_root}/LibriSpeech/train-clean-5/7859/102519/7859-102519-0036.flac",
    "length": 11.965,
    "spk_id": "7859"
  },
}

As you can see, we have a hierarchical structure in which the first key is a unique identifier of the spoken sentence. Then, we specify all the fields that are needed for the task addressed. For instance, we report the path of the speech recording, its length in seconds (needed if we wanna sort the sentences before creating the mini-batches), and the speaker identity of the speaker in the given recording.

Actually, you can specify here all entries that you need (language-id, emotion annotation, etc). However, there must be a matching between the name of these entries and what the experiment script (e.g, train.py) expects. We will elaborate more on this later.

You might have noticed that we define a special variable called data_root. This allows users to dynamically change the data folder from the command line (or from the yaml hyperparameter file).

Preparation Script

Every dataset is formatted in a different way. The script that parses your own dataset and creates the JSON or the CSV files is something that you are supposed to write. Most of the time, this is very straightforward.

For the mini-librispeech dataset, for instance, we wrote this simple data preparation script called mini_librispeech_prepare.py.

This function automatically downloads the data (that in this case are publicly available). We search for all the audio files and while reading them we create the JSON file with the speaker-id annotation.

You can use this script as a good base for your custom preparation on your target dataset. As you can see, we create three separate data manifest files to manage training, validation, and test phases.

Copy your data locally

When using speechbrain (or any other toolkit) within an HPC cluster, a good practice is to compress your dataset in a single file and copy (and uncompress) the data in the local folder of the computing node. This would make the code much much faster because the data aren’t fetched from the shared filesystem but from the local one. Moreover, you don’t harm the performance of the shared filesystem with tons of reading operations. We strongly suggest users follow this approach (not possible here in Google Colab).

Step 2: Train the classifier

We show now how we can train an utterance-level classifier with SpeechBrain. The proposed recipe performs a feature computation/normalization, processes the features with an encoder, and applies a classifier on top of that. Data augmentation is also employed to improve system performance.

Train a speaker-id model

We are going to train the TDNN-based model used for x-vectors. Statistical pooling is used on the top of the convolutional layers to convert a variable-length sentence into a fixed-length embeddings.

On the top of the embeddings, a simple fully-connected classifier is employed to predict which of the N speakers is active in the given sentence.

To train this model, run the following code:

%cd /content/speechbrain/templates/speaker_id
!python train.py train.yaml --number_of_epochs=15 #--device='cpu'

/content/speechbrain/templates/speaker_id
speechbrain.core - Beginning experiment!
speechbrain.core - Experiment folder: ./results/speaker_id/1986
Downloading http://www.openslr.org/resources/31/train-clean-5.tar.gz to ./data/train-clean-5.tar.gz
train-clean-5.tar.gz: 333MB [00:18, 18.2MB/s]               
mini_librispeech_prepare - Creating train.json, valid.json, and test.json
mini_librispeech_prepare - train.json successfully created!
mini_librispeech_prepare - valid.json successfully created!
mini_librispeech_prepare - test.json successfully created!
Downloading https://www.dropbox.com/scl/fi/a09pj97s5ifan81dqhi4n/noises.zip?rlkey=j8b0n9kdjdr32o1f06t0cw5b7&dl=1 to ./data/noise/data.zip
noises.zip?rlkey=j8b0n9kdjdr32o1f06t0cw5b7&dl=1: 569MB [00:05, 105MB/s]               
Extracting ./data/noise/data.zip to ./data/noise
speechbrain.dataio.encoder - Load called, but CategoricalEncoder is not empty. Loaded data will overwrite everything. This is normal if there is e.g. an unk label defined at init.
speechbrain.core - Info: ckpt_interval_minutes arg from hparam file is used
speechbrain.core - Exception:
Traceback (most recent call last):
  File "/content/speechbrain/templates/speaker_id/train.py", line 307, in <module>
    spk_id_brain = SpkIdBrain(
  File "/usr/local/lib/python3.10/dist-packages/speechbrain/core.py", line 695, in __init__
    torch.cuda.set_device(int(self.device[-1]))
  File "/usr/local/lib/python3.10/dist-packages/torch/cuda/__init__.py", line 404, in set_device
    torch._C._cuda_setDevice(device)
  File "/usr/local/lib/python3.10/dist-packages/torch/cuda/__init__.py", line 298, in _lazy_init
    torch._C._cuda_init()
RuntimeError: Found no NVIDIA driver on your system. Please check that you have an NVIDIA GPU and installed a driver from http://www.nvidia.com/Download/index.aspx

As you can see from the prints, both the validation and training losses are decreasing very fast in the first epochs. Then, we basically see some minor improvements and performance oscillations.

At the end of the training, the validation error should go to zero (or very close to zero).

The task proposed in this tutorial is very easy because we only have to classify the 28 speakers of the mini-librispeech dataset. Take this tutorial just as an example that explains how to set up all the needed components to develop a speech classifier. Please, refer to our voxceleb recipes if you would like to see an example on a popular speaker recognition dataset

Before diving into the code, let’s see which files/folders are generated in the specified output_folder:

train_log.txt: contains the statistics (e.g, train_loss, valid_loss) computed at each epoch.
log.txt: is a more detailed logger containing the timestamps for each basic operation.
env.log: shows all the dependencies used with their corresponding version (useful for replicability).
train.py, hyperparams.yaml: are a copy of the experiment file along with the corresponding hyperparameters (for replicability).
save: is the place where we store the learned model.
In the save folder, you find subfolders containing the checkpoints saved during training (in the format CKPT+data+time). Typically, you find here two checkpoints: the best (i.e, the oldest one) and the latest (i.e, the most recent one). If you find only a single checkpoint it means that the last epoch is also the best.

Inside each checkpoint, we store all the information needed to resume training (e.g, models, optimizers, schedulers, epoch counter, etc.). The parameters of the embedding models are reported in embedding_model.ckpt file, while the ones of the classifier are in classifier.ckpt. This is just a binary format readable with torch.load.

The save folder contains the label encoder (label_encoder.txt) as well, which maps each speaker-id entry to their corresponding indexes.

'163' => 0
'7312' => 1
'7859' => 2
'19' => 3
'1737' => 4
'6272' => 5
'1970' => 6
'2416' => 7
'118' => 8
'6848' => 9
'4680' => 10
'460' => 11
'3664' => 12
'3242' => 13
'1898' => 14
'7367' => 15
'1088' => 16
'3947' => 17
'3526' => 18
'1867' => 19
'8629' => 20
'332' => 21
'4640' => 22
'2136' => 23
'669' => 24
'5789' => 25
'32' => 26
'226' => 27
================
'starting_index' => 0

As usual, we implement the system with an experiment file train.py and a hyperparameter file called train.yaml.

Hyperparameters

The yaml file contains all the modules and hyperparameters need to implement the desired classifier. You can take a look into the full train.yaml file here.

In the first part, we specify some basic settings, such as the seed and the path of the output folder:

# Seed needs to be set at top of yaml, before objects with parameters are made
seed: 1986
__set_seed: !!python/object/apply:torch.manual_seed [!ref <seed>]

# If you plan to train a system on an HPC cluster with a big dataset,
# we strongly suggest doing the following:
# 1- Compress the dataset in a single tar or zip file.
# 2- Copy your dataset locally (i.e., the local disk of the computing node).
# 3- Uncompress the dataset in the local folder.
# 4- Set data_folder with the local path.
# Reading data from the local disk of the compute node (e.g. $SLURM_TMPDIR with SLURM-based clusters) is very important.
# It allows you to read the data much faster without slowing down the shared filesystem.
data_folder: ./data
output_folder: !ref ./results/speaker_id/<seed>
save_folder: !ref <output_folder>/save
train_log: !ref <output_folder>/train_log.txt

We then specify the path of the data manifest files for training, validation, and test:

# Path where data manifest files will be stored
# The data manifest files are created by the data preparation script.
train_annotation: train.json
valid_annotation: valid.json
test_annotation: test.json

These files will be automatically created when calling the data preparation script (mini_librispeech_prepare.py) from the experiment file (train.py).

Next, we set up the train_logger and declare the error_stats objects that will gather statistics on the classification error rate:

# The train logger writes training statistics to a file, as well as stdout.
train_logger: !new:speechbrain.utils.train_logger.FileTrainLogger
    save_file: !ref <train_log>

error_stats: !name:speechbrain.utils.metric_stats.MetricStats
    metric: !name:speechbrain.nnet.losses.classification_error
        reduction: batch

We can now specify some training hyperparameters such as the number of epochs, the batch size, the learning rate, the number of epochs, and the embedding dimensionality.

ckpt_interval_minutes: 15 # save checkpoint every N min

# Feature parameters
n_mels: 23

# Training Parameters
sample_rate: 16000
number_of_epochs: 35
batch_size: 16
lr_start: 0.001
lr_final: 0.0001
n_classes: 28 # In this case, we have 28 speakers
emb_dim: 512 # dimensionality of the embeddings
dataloader_options:
    batch_size: !ref <batch_size>

The variable ckpt_interval_minutes can be used to save checkpoints every N minutes within a training epoch. In some cases, one epoch might take several hours, and saving the checkpoint periodically is a good and safe practice. This feature is not really needed for this simple tutorial based on a tiny dataset.

We can now define the most important modules that are needed to train our model:

# Added noise and reverb come from OpenRIR dataset, automatically
# downloaded and prepared with this Environmental Corruption class.
env_corrupt: !new:speechbrain.lobes.augment.EnvCorrupt
    openrir_folder: !ref <data_folder>
    babble_prob: 0.0
    reverb_prob: 0.0
    noise_prob: 1.0
    noise_snr_low: 0
    noise_snr_high: 15

# Adds speech change + time and frequency dropouts (time-domain implementation)
# # A small speed change help to improve the performance of speaker-id as well.
augmentation: !new:speechbrain.lobes.augment.TimeDomainSpecAugment
    sample_rate: !ref <sample_rate>
    speeds: [95, 100, 105]

# Feature extraction
compute_features: !new:speechbrain.lobes.features.Fbank
    n_mels: !ref <n_mels>

# Mean and std normalization of the input features
mean_var_norm: !new:speechbrain.processing.features.InputNormalization
    norm_type: sentence
    std_norm: False

# To design a custom model, either just edit the simple CustomModel
# class that's listed here, or replace this `!new` call with a line
# pointing to a different file you've defined.
embedding_model: !new:custom_model.Xvector
    in_channels: !ref <n_mels>
    activation: !name:torch.nn.LeakyReLU
    tdnn_blocks: 5
    tdnn_channels: [512, 512, 512, 512, 1500]
    tdnn_kernel_sizes: [5, 3, 3, 1, 1]
    tdnn_dilations: [1, 2, 3, 1, 1]
    lin_neurons: !ref <emb_dim>

classifier: !new:custom_model.Classifier
    input_shape: [null, null, !ref <emb_dim>]
    activation: !name:torch.nn.LeakyReLU
    lin_blocks: 1
    lin_neurons: !ref <emb_dim>
    out_neurons: !ref <n_classes>

# The first object passed to the Brain class is this "Epoch Counter"
# which is saved by the Checkpointer so that training can be resumed
# if it gets interrupted at any point.
epoch_counter: !new:speechbrain.utils.epoch_loop.EpochCounter
    limit: !ref <number_of_epochs>

# Objects in "modules" dict will have their parameters moved to the correct
# device, as well as having train()/eval() called on them by the Brain class.
modules:
    compute_features: !ref <compute_features>
    env_corrupt: !ref <env_corrupt>
    augmentation: !ref <augmentation>
    embedding_model: !ref <embedding_model>
    classifier: !ref <classifier>
    mean_var_norm: !ref <mean_var_norm>

The augmentation part is based on both env_corrupt (that adds noise and reverberation) and augmentation(that adds time/frequency dropouts and speed change). For more information on these modules, please take a look at the tutorials on enviromental corruption and the one on speech augmentation.

We conclude the hyperparameter specification with the declaration of the optimizer, learning rate scheduler, and the checkpointer:

# This optimizer will be constructed by the Brain class after all parameters
# are moved to the correct device. Then it will be added to the checkpointer.
opt_class: !name:torch.optim.Adam
    lr: !ref <lr_start>

# This function manages learning rate annealing over the epochs.
# We here use the simple lr annealing method that linearly decreases
# the lr from the initial value to the final one.
lr_annealing: !new:speechbrain.nnet.schedulers.LinearScheduler
    initial_value: !ref <lr_start>
    final_value: !ref <lr_final>
    epoch_count: !ref <number_of_epochs>

# This object is used for saving the state of training both so that it
# can be resumed if it gets interrupted, and also so that the best checkpoint
# can be later loaded for evaluation or inference.
checkpointer: !new:speechbrain.utils.checkpoints.Checkpointer
    checkpoints_dir: !ref <save_folder>
    recoverables:
        embedding_model: !ref <embedding_model>
        classifier: !ref <classifier>
        normalizer: !ref <mean_var_norm>
        counter: !ref <epoch_counter>

In this case, we use Adam as an optimizer and a linear learning rate decay over the 15 epochs.

Let’s now save the best model into a separate folder (useful for the inference part explained later):

# Create folder for best model
!mkdir /content/best_model/

# Copy label encoder
!cp results/speaker_id/1986/save/label_encoder.txt /content/best_model/

# Copy best model
!cp "`ls -td results/speaker_id/1986/save/CKPT* | tail -1`"/* /content/best_model/

ls: cannot access 'results/speaker_id/1986/save/CKPT*': No such file or directory
cp: -r not specified; omitting directory '/bin'
cp: -r not specified; omitting directory '/boot'
cp: -r not specified; omitting directory '/content'
cp: -r not specified; omitting directory '/datalab'
cp: -r not specified; omitting directory '/dev'
cp: -r not specified; omitting directory '/etc'
cp: -r not specified; omitting directory '/home'
cp: -r not specified; omitting directory '/kaggle'
cp: -r not specified; omitting directory '/lib'
cp: -r not specified; omitting directory '/lib32'
cp: -r not specified; omitting directory '/lib64'
cp: -r not specified; omitting directory '/libx32'
cp: -r not specified; omitting directory '/media'
cp: -r not specified; omitting directory '/mnt'
cp: -r not specified; omitting directory '/opt'
cp: -r not specified; omitting directory '/proc'
cp: -r not specified; omitting directory '/root'
cp: -r not specified; omitting directory '/run'
cp: -r not specified; omitting directory '/sbin'
cp: -r not specified; omitting directory '/srv'
cp: -r not specified; omitting directory '/sys'
cp: -r not specified; omitting directory '/tmp'
cp: -r not specified; omitting directory '/tools'
cp: -r not specified; omitting directory '/usr'
cp: -r not specified; omitting directory '/var'

Experiment file

Let’s now take a look into how the objects, functions, and hyperparameters declared in the yaml file are used in train.py to implement the classifier.

Let’s start from the main of the train.py:

# Recipe begins!
if __name__ == "__main__":

    # Reading command line arguments.
    hparams_file, run_opts, overrides = sb.parse_arguments(sys.argv[1:])

    # Initialize ddp (useful only for multi-GPU DDP training).
    sb.utils.distributed.ddp_init_group(run_opts)

    # Load hyperparameters file with command-line overrides.
    with open(hparams_file) as fin:
        hparams = load_hyperpyyaml(fin, overrides)

    # Create experiment directory
    sb.create_experiment_directory(
        experiment_directory=hparams["output_folder"],
        hyperparams_to_save=hparams_file,
        overrides=overrides,
    )

    # Data preparation, to be run on only one process.
    sb.utils.distributed.run_on_main(
        prepare_mini_librispeech,
        kwargs={
            "data_folder": hparams["data_folder"],
            "save_json_train": hparams["train_annotation"],
            "save_json_valid": hparams["valid_annotation"],
            "save_json_test": hparams["test_annotation"],
            "split_ratio": [80, 10, 10],
        },
    )

We here do some preliminary operations such as parsing the command line, initializing the distributed data-parallel (needed if multiple GPUs are used), creating the output folder, and reading the yaml file.

After reading the yaml file with load_hyperpyyaml, all the objects declared in the hyperparameter files are initialized and available in a dictionary form (along with the other functions and parameters reported in the yaml file). For instance, we will have hparams['embedding_model'], hparams['classifier'], hparams['batch_size'], etc.

We also run the data preparation script prepare_mini_librispeech that creates the data manifest files. It is wrapped with sb.utils.distributed.run_on_main because this operation writes the manifest files on disk and this must be done on a single process even in a multi-GPU DDP scenario. For more information on how to use multiple GPUs, please take a look into this tutorial.

Data-IO Pipeline

We then call a special function that creates the dataset objects for training, validation, and test.

    # Create dataset objects "train", "valid", and "test".
    datasets = dataio_prep(hparams)

Let’s take a closer look into that.

def dataio_prep(hparams):
    """This function prepares the datasets to be used in the brain class.
    It also defines the data processing pipeline through user-defined functions.
    We expect `prepare_mini_librispeech` to have been called before this,
    so that the `train.json`, `valid.json`,  and `valid.json` manifest files
    are available.
    Arguments
    ---------
    hparams : dict
        This dictionary is loaded from the `train.yaml` file, and it includes
        all the hyperparameters needed for dataset construction and loading.
    Returns
    -------
    datasets : dict
        Contains two keys, "train" and "valid" that correspond
        to the appropriate DynamicItemDataset object.
    """

    # Initialization of the label encoder. The label encoder assignes to each
    # of the observed label a unique index (e.g, 'spk01': 0, 'spk02': 1, ..)
    label_encoder = sb.dataio.encoder.CategoricalEncoder()

    # Define audio pipeline
    @sb.utils.data_pipeline.takes("wav")
    @sb.utils.data_pipeline.provides("sig")
    def audio_pipeline(wav):
        """Load the signal, and pass it and its length to the corruption class.
        This is done on the CPU in the `collate_fn`."""
        sig = sb.dataio.dataio.read_audio(wav)
        return sig

    # Define label pipeline:
    @sb.utils.data_pipeline.takes("spk_id")
    @sb.utils.data_pipeline.provides("spk_id", "spk_id_encoded")
    def label_pipeline(spk_id):
        yield spk_id
        spk_id_encoded = label_encoder.encode_label_torch(spk_id)
        yield spk_id_encoded

    # Define datasets. We also connect the dataset with the data processing
    # functions defined above.
    datasets = {}
    hparams["dataloader_options"]["shuffle"] = False
    for dataset in ["train", "valid", "test"]:
        datasets[dataset] = sb.dataio.dataset.DynamicItemDataset.from_json(
            json_path=hparams[f"{dataset}_annotation"],
            replacements={"data_root": hparams["data_folder"]},
            dynamic_items=[audio_pipeline, label_pipeline],
            output_keys=["id", "sig", "spk_id_encoded"],
        )

    # Load or compute the label encoder (with multi-GPU DDP support)
    # Please, take a look into the lab_enc_file to see the label to index
    # mappinng.
    lab_enc_file = os.path.join(hparams["save_folder"], "label_encoder.txt")
    label_encoder.load_or_create(
        path=lab_enc_file,
        from_didatasets=[datasets["train"]],
        output_key="spk_id",
    )

    return datasets

The first part is just a declaration of the CategoricalEncoder that will be used to convert categorical labels into their corresponding indexes.

You can then notice that we expose the audio and label processing functions.

The audio_pipeline takes the path of the audio signal (wav) and reads it. It returns a tensor containing the read speech sentence. The entry in input to this function (i.e, wav) must have the same name of the corresponding key in the data manifest file:

{
  "163-122947-0045": {
    "wav": "{data_root}/LibriSpeech/train-clean-5/163/122947/163-122947-0045.flac",
    "length": 14.335,
    "spk_id": "163"
  },
}

Similarly, we define another function called label_pipeline for processing the utterance-level labels and put them in a format usable by the defined model. The function reads the string spk_id defined in the JSON file and encodes it with the categorical encoder.

We then create the DynamicItemDataset and connect it with the processing functions defined above. We define the desired output keys to expose. These keys will be available in the brain class within the batch variable as:

batch.id
batch.sig
batch.spk_id_encoded
The last part of the function is dedicated to the initialization of the label encoder. The label encoder takes in input the training dataset and assigns a different index to all the spk_id entries founded. These indexes will correspond to the output indexes of the classifier.

For more information on the data loader, please take a look into this tutorial

After the definition of the datasets, the main function can go ahead with the initialization and use of the brain class:

    # Initialize the Brain object to prepare for mask training.
    spk_id_brain = SpkIdBrain(
        modules=hparams["modules"],
        opt_class=hparams["opt_class"],
        hparams=hparams,
        run_opts=run_opts,
        checkpointer=hparams["checkpointer"],
    )

    # The `fit()` method iterates the training loop, calling the methods
    # necessary to update the parameters of the model. Since all objects
    # with changing state are managed by the Checkpointer, training can be
    # stopped at any point, and will be resumed on next call.
    spk_id_brain.fit(
        epoch_counter=spk_id_brain.hparams.epoch_counter,
        train_set=datasets["train"],
        valid_set=datasets["valid"],
        train_loader_kwargs=hparams["dataloader_options"],
        valid_loader_kwargs=hparams["dataloader_options"],
    )

    # Load the best checkpoint for evaluation
    test_stats = spk_id_brain.evaluate(
        test_set=datasets["test"],
        min_key="error",
        test_loader_kwargs=hparams["dataloader_options"],
    )

The fit method performs training, while the test is performed with the evaluate one. The training and validation data loaders are given in input to the fit method, while the test dataset is fed into the evaluate method.

Let’s now take a look into the most important methods defined in the brain class.

Forward Computations

Let’s start with the forward function, which defines all the computations needed to transform the input audio into the output predictions.

    def compute_forward(self, batch, stage):
        """Runs all the computation of that transforms the input into the
        output probabilities over the N classes.
        Arguments
        ---------
        batch : PaddedBatch
            This batch object contains all the relevant tensors for computation.
        stage : sb.Stage
            One of sb.Stage.TRAIN, sb.Stage.VALID, or sb.Stage.TEST.
        Returns
        -------
        predictions : Tensor
            Tensor that contains the posterior probabilities over the N classes.
        """

        # We first move the batch to the appropriate device.
        batch = batch.to(self.device)

        # Compute features, embeddings, and predictions
        feats, lens = self.prepare_features(batch.sig, stage)
        embeddings = self.modules.embedding_model(feats, lens)
        predictions = self.modules.classifier(embeddings)

        return predictions

In this case, the chain of computation is very simple. We just put the batch on the right device and compute the acoustic features. We then process the features with the TDNN encoder that outputs a fixed-size tensor. The latter feeds a classifier that outputs the posterior probabilities over the N classes (in this case the 28 speakers). Data augmentation is added in the prepare_features method:

    def prepare_features(self, wavs, stage):
        """Prepare the features for computation, including augmentation.
        Arguments
        ---------
        wavs : tuple
            Input signals (tensor) and their relative lengths (tensor).
        stage : sb.Stage
            The current stage of training.
        """
        wavs, lens = wavs

        # Add augmentation if specified. In this version of augmentation, we
        # concatenate the original and the augment batches in a single bigger
        # batch. This is more memory-demanding, but helps to improve the
        # performance. Change it if you run OOM.
        if stage == sb.Stage.TRAIN:
            if hasattr(self.modules, "env_corrupt"):
                wavs_noise = self.modules.env_corrupt(wavs, lens)
                wavs = torch.cat([wavs, wavs_noise], dim=0)
                lens = torch.cat([lens, lens])

            if hasattr(self.hparams, "augmentation"):
                wavs = self.hparams.augmentation(wavs, lens)

        # Feature extraction and normalization
        feats = self.modules.compute_features(wavs)
        feats = self.modules.mean_var_norm(feats, lens)

        return feats, lens

In particular, when the environmental corruption is declared in the yaml file, we concatenate in the same batch both the clean and the augmented version of the signals.

This approach doubles the batch size (and this the needed GPU memory), but it implements a very powerful regularizer. Having both the clean and the noisy version of the signal within the same batch forces the gradient to point into a direction of the parameter space that is robust against signal distortions.

Compute Objectives

Let’s take a look now into the compute_objectives method that takes in input the targets, the predictions, and estimates a loss function:

    def compute_objectives(self, predictions, batch, stage):
        """Computes the loss given the predicted and targeted outputs.
        Arguments
        ---------
        predictions : tensor
            The output tensor from `compute_forward`.
        batch : PaddedBatch
            This batch object contains all the relevant tensors for computation.
        stage : sb.Stage
            One of sb.Stage.TRAIN, sb.Stage.VALID, or sb.Stage.TEST.
        Returns
        -------
        loss : torch.Tensor
            A one-element tensor used for backpropagating the gradient.
        """

        _, lens = batch.sig
        spkid, _ = batch.spk_id_encoded

        # Concatenate labels (due to data augmentation)
        if stage == sb.Stage.TRAIN and hasattr(self.modules, "env_corrupt"):
            spkid = torch.cat([spkid, spkid], dim=0)
            lens = torch.cat([lens, lens])

        # Compute the cost function
        loss = sb.nnet.losses.nll_loss(predictions, spkid, lens)

        # Append this batch of losses to the loss metric for easy
        self.loss_metric.append(
            batch.id, predictions, spkid, lens, reduction="batch"
        )

        # Compute classification error at test time
        if stage != sb.Stage.TRAIN:
            self.error_metrics.append(batch.id, predictions, spkid, lens)

        return loss

The predictions in input are those computed in the forward method. The cost function is evaluated by comparing these predictions with the target labels. This is done with the Negative Log-Likelihood (NLL) loss.

####Other methods Beyond these two important functions, we have some other methods that are used by the brain class. The on_state_starts gets called at the beginning of each epoch and it is used to set up statistics trackers. The on_stage_end one is called at the end of each stage (e.g, at the end of each training epoch) and mainly takes care of statistic management, learning rate annealing, and checkpointing. For a more detailed description of the brain class, please take a look into this tutorial. For more information on checkpointing, take a look here

Step 3: Inference

At this point, we can use the trained classifier to perform predictions on new data. Speechbrain made available some classes (take a look here) such as the EncoderClassifier one that can make inference easier. The class can also be used to extract some embeddings at the output of the encoder.

Let’s see first how can we used it to load our best xvector model (trained on Voxceleb and stored on HuggingFace) to compute some embeddings and perform a speaker classification:

import torchaudio
from speechbrain.inference.classifiers import EncoderClassifier
classifier = EncoderClassifier.from_hparams(source="speechbrain/spkrec-xvect-voxceleb")
signal, fs =torchaudio.load('/content/speechbrain/tests/samples/single-mic/example1.wav')

# Compute speaker embeddings
embeddings = classifier.encode_batch(signal)

# Perform classification
output_probs, score, index, text_lab = classifier.classify_batch(signal)

# Posterior log probabilities
print(output_probs)

# Score (i.e, max log posteriors)
print(score)

# Index of the predicted speaker
print(index)

# Text label of the predicted speaker
print(text_lab)

tensor([[-31.8672, -35.2024, -25.7930,  ..., -21.0044, -12.4279, -21.5265]])
tensor([-1.1278])
tensor([2710])
['id10892']

For those of you interested in speaker verification, we also created an inference interface called SpeakerRecognition:

from speechbrain.inference.speaker import SpeakerRecognition
verification = SpeakerRecognition.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb", savedir="pretrained_models/spkrec-ecapa-voxceleb")

file1 = '/content/speechbrain/tests/samples/single-mic/example1.wav'
file2 = '/content/speechbrain/tests/samples/single-mic/example2.flac'

score, prediction = verification.verify_files(file1, file2)

print(score)
print(prediction) # True = same speaker, False=Different speakers

tensor([0.1799])
tensor([False])

But, how does this work with our custom classifier that we trained before?

At this point, some options are available to you. For a full overview of all of them, please take a look into this tutorial.

We here only show how you can use the existing EncoderClassifier on the model that we just trained.

Use the EncoderClassifier interface on your model

The EncoderClassifier class takes a pre-trained model and performs inference on it with the following methods:

encode_batch: applies the encoder to an input batch and returns some encoded embeddings.
classify_batch: performs a full classification step and returns the output probabilities of the classifier, the best score, the index of the best class, and its label in text format (see example above).
To use this interface with the model trained before, we have to create an inference yaml file which is a bit different from that use for training. The main differences are the following:

You can remove all the hyperparameters and objects needed for training only. You can just keep the part related to the model definition.
You have to allocate a Categorical encoder object that allows you to transform indexes into text labels.
You have to use the pre-trainer to link your model with their corresponding files.
The inference yaml file looks like that:

%%writefile /content/best_model/hparams_inference.yaml

# #################################
# Basic inference parameters for speaker-id. We have first a network that
# computes some embeddings. On the top of that, we employ a classifier.
#
# Author:
#  * Mirco Ravanelli 2021
# #################################

# pretrain folders:
pretrained_path: /content/best_model/


# Model parameters
n_mels: 23
sample_rate: 16000
n_classes: 28 # In this case, we have 28 speakers
emb_dim: 512 # dimensionality of the embeddings

# Feature extraction
compute_features: !new:speechbrain.lobes.features.Fbank
    n_mels: !ref <n_mels>

# Mean and std normalization of the input features
mean_var_norm: !new:speechbrain.processing.features.InputNormalization
    norm_type: sentence
    std_norm: False

# To design a custom model, either just edit the simple CustomModel
# class that's listed here, or replace this `!new` call with a line
# pointing to a different file you've defined.
embedding_model: !new:custom_model.Xvector
    in_channels: !ref <n_mels>
    activation: !name:torch.nn.LeakyReLU
    tdnn_blocks: 5
    tdnn_channels: [512, 512, 512, 512, 1500]
    tdnn_kernel_sizes: [5, 3, 3, 1, 1]
    tdnn_dilations: [1, 2, 3, 1, 1]
    lin_neurons: !ref <emb_dim>

classifier: !new:custom_model.Classifier
    input_shape: [null, null, !ref <emb_dim>]
    activation: !name:torch.nn.LeakyReLU
    lin_blocks: 1
    lin_neurons: !ref <emb_dim>
    out_neurons: !ref <n_classes>

label_encoder: !new:speechbrain.dataio.encoder.CategoricalEncoder

# Objects in "modules" dict will have their parameters moved to the correct
# device, as well as having train()/eval() called on them by the Brain class.
modules:
    compute_features: !ref <compute_features>
    embedding_model: !ref <embedding_model>
    classifier: !ref <classifier>
    mean_var_norm: !ref <mean_var_norm>

pretrainer: !new:speechbrain.utils.parameter_transfer.Pretrainer
    loadables:
        embedding_model: !ref <embedding_model>
        classifier: !ref <classifier>
        label_encoder: !ref <label_encoder>
    paths:
        embedding_model: !ref <pretrained_path>/embedding_model.ckpt
        classifier: !ref <pretrained_path>/classifier.ckpt
        label_encoder: !ref <pretrained_path>/label_encoder.txt

Writing /content/best_model/hparams_inference.yaml

As you can see, we only have the model definition here (not optimizers, checkpoiter, etc). The last part of the yaml file manages pretraining, where we bind model objects with their pre-training files created at training time.

Let’s now perform inference with the EncoderClassifier class:

from speechbrain.inference.classifiers import EncoderClassifier

classifier = EncoderClassifier.from_hparams(source="/content/best_model/", hparams_file='hparams_inference.yaml', savedir="/content/best_model/")

# Perform classification
audio_file = 'data/LibriSpeech/train-clean-5/5789/70653/5789-70653-0036.flac'
signal, fs = torchaudio.load(audio_file) # test_speaker: 5789
output_probs, score, index, text_lab = classifier.classify_batch(signal)
print('Target: 5789, Predicted: ' + text_lab[0])

# Another speaker
audio_file = 'data/LibriSpeech/train-clean-5/460/172359/460-172359-0012.flac'
signal, fs =torchaudio.load(audio_file) # test_speaker: 460
output_probs, score, index, text_lab = classifier.classify_batch(signal)
print('Target: 460, Predicted: ' + text_lab[0])

# And if you want to extract embeddings...
embeddings = classifier.encode_batch(signal)

---------------------------------------------------------------------------
OSError                                   Traceback (most recent call last)
/usr/lib/python3.10/pathlib.py in resolve(self, strict)
   1086             try:
-> 1087                 p.stat()
   1088             except OSError as e:

/usr/lib/python3.10/pathlib.py in stat(self, follow_symlinks)
   1096         """
-> 1097         return self._accessor.stat(self, follow_symlinks=follow_symlinks)
   1098 

OSError: [Errno 40] Too many levels of symbolic links: '/content/best_model/embedding_model.ckpt'

During handling of the above exception, another exception occurred:

RuntimeError                              Traceback (most recent call last)
<ipython-input-7-c0f62d2f5dc4> in <cell line: 3>()
      1 from speechbrain.inference.classifiers import EncoderClassifier
      2 
----> 3 classifier = EncoderClassifier.from_hparams(source="/content/best_model/", hparams_file='hparams_inference.yaml', savedir="/content/best_model/")
      4 
      5 # Perform classification

/usr/local/lib/python3.10/dist-packages/speechbrain/inference/interfaces.py in from_hparams(cls, source, hparams_file, pymodule_file, overrides, savedir, use_auth_token, revision, download_only, huggingface_cache_dir, **kwargs)
    488         pretrainer.set_collect_in(savedir)
    489         # For distributed setups, have this here:
--> 490         run_on_main(pretrainer.collect_files, kwargs={"default_source": source})
    491         # Load on the CPU. Later the params can be moved elsewhere by specifying
    492         if not download_only:

/usr/local/lib/python3.10/dist-packages/speechbrain/utils/distributed.py in run_on_main(func, args, kwargs, post_func, post_args, post_kwargs, run_post_on_main)
     58         post_kwargs = {}
     59 
---> 60     main_process_only(func)(*args, **kwargs)
     61     ddp_barrier()
     62 

/usr/local/lib/python3.10/dist-packages/speechbrain/utils/distributed.py in main_proc_wrapped_func(*args, **kwargs)
    100         MAIN_PROC_ONLY += 1
    101         if if_main_process():
--> 102             result = function(*args, **kwargs)
    103         else:
    104             result = None

/usr/local/lib/python3.10/dist-packages/speechbrain/utils/parameter_transfer.py in collect_files(self, default_source, internal_ddp_handling)
    258                 fetch_from, source = source
    259             if fetch_from is FetchFrom.LOCAL or (
--> 260                 pathlib.Path(path).resolve()
    261                 == pathlib.Path(source).resolve() / filename
    262             ):

/usr/lib/python3.10/pathlib.py in resolve(self, strict)
   1087                 p.stat()
   1088             except OSError as e:
-> 1089                 check_eloop(e)
   1090         return p
   1091 

/usr/lib/python3.10/pathlib.py in check_eloop(e)
   1072             winerror = getattr(e, 'winerror', 0)
   1073             if e.errno == ELOOP or winerror == _WINERROR_CANT_RESOLVE_FILENAME:
-> 1074                 raise RuntimeError("Symlink loop from %r" % e.filename)
   1075 
   1076         try:

RuntimeError: Symlink loop from '/content/best_model/embedding_model.ckpt'

The EncoderClassifier interface assumes that your model has the following modules specified in the yaml file:

compute_features: that manages feature extraction from the raw audio signal
mean_var_norm: that performs feature normalization
embedding_model: that converts features into fix-size embeddings.
classifier: that performs a final classification over N classes on the top o the embeddings.
If your model cannot be structured in this way, you can always customize the EncoderClassifier interface to fulfill your needs. Please, take a look into this tutorial for more information.

Extension to different tasks

In a general case, you might have your own data and classification task and you would like to use your own model. Let’s comment a bit more on how you can customize your recipe.

Suggestion: start from a recipe that is working (like the one used for this template) and only do the minimal modifications needed to customize it. Test your model step by step. Make sure your model can overfit on a tiny dataset composed of few sentences. If it doesn’t overfit there is likely a bug in your model.

Train with your data on your task

What about if I have to solve another utterance-level classification task such as language-id, emotion recognition, sound classification, keyword spotting on my data?

All you have to do is:

Change the JSON with the annotations needed for your task.
Change the data pipeline in train.py to be compliant with the new annotations.
Change the JSON

This tutorial expects JSON files like this:

{
  "163-122947-0045": {
    "wav": "{data_root}/LibriSpeech/train-clean-5/163/122947/163-122947-0045.flac",
    "length": 14.335,
    "spk_id": "163"
  },
  "7312-92432-0025": {
    "wav": "{data_root}/LibriSpeech/train-clean-5/7312/92432/7312-92432-0025.flac",
    "length": 12.01,
    "spk_id": "7312"
  },
  "7859-102519-0036": {
    "wav": "{data_root}/LibriSpeech/train-clean-5/7859/102519/7859-102519-0036.flac",
    "length": 11.965,
    "spk_id": "7859"
  },
}

However, you can add here all the entries that you want. For instance, if you would like to solve a language-id task, the JSON file should look like this:

{
  "sentence001": {
    "wav": "{data_root}/your_path/your_file1.wav",
    "length": 10.335,
    "lang_id": "Italian"
  },
{
  "sentence002": {
    "wav": "{data_root}/your_path/your_file2.wav",
    "length": 12.335,
    "lang_id": "French"
  },
}

If you would like to solve an emotion recognition task, it will look like that:

{
  "sentence001": {
    "wav": "{data_root}/your_path/your_file1.wav",
    "length": 10.335,
    "emotion": "Happy"
  },
{
  "sentence002": {
    "wav": "{data_root}/your_path/your_file2.wav",
    "length": 12.335,
    "emotion": "Sad"
  },
}

To create the data manifest files, you have to parse your dataset and create JSON files with a unique ID for each sentence, the path of the audio signal (wav), the length of the speech sentence in seconds (length), and the annotations that you want.

Change train.py

The only thing to remember is that the name entries in the JSON file must match with what the dataloader expectes in train.py. For instance, if you defined an emotion key in JSON, you should have it in the dataio pipeline of train.py something like this:

    # Define label pipeline:
    @sb.utils.data_pipeline.takes("emotion")
    @sb.utils.data_pipeline.provides("emotion", "emotion_encoded")
    def label_pipeline(emotion):
        yield emotion
        emotion_encoded = label_encoder.encode_label_torch(emotion)
        yield emotion_encoded

Basically, you have to replace the spk_id entry with the emotion one everywhere in the code. That’s all!

Train with your own model

At some point, you might have your own model and you would like to plug it into the speech recognition pipeline. For instance, you might wanna replace our xvector encoder with something different.

To do that, you have to create your own class and specify there the list of computations for your neural network. You can take a look into the models already existing in speechbrain.lobes.models. If your model is a plain pipeline of computations, you can use the sequential container. If the model is a more complex chain of computations, you can create it as an instance of torch.nn.Module and define there the __init__ and forward methods like here.

Once you defined your model, you only have to declare it in the yaml file and use it in train.py

Important:
When plugging a new model, you have to tune again the most important hyperparameters of the system (e.g, learning rate, batch size, and the architectural parameters) to make it working well.

ECAPA-TDNN model

One model that we find particularly effective for speaker recognition is the ECAPA-TDNN one implemented here.

The ECAPA-TDNN architecture is based on the popular x-vector topology and it introduces several enhancements to create more robust speaker embeddings.

The pooling layer uses a channel- and context-dependent attention mechanism, which allows the network to attend different frames per channel. 1-dimensional SqueezeExcitation (SE) blocks rescale the channels of the intermediate frame-level feature maps to insert global context information in the locally operating convolutional blocks. Next, the integration of 1-dimensional Res2-blocks improves performance while simultaneously reducing the total parameter count by using grouped convolutions in a hierarchical way.

Finally, Multi-layer Feature Aggregation (MFA) merges complementary information before the statistics pooling by concatenating the final frame-level feature map with an intermediate feature maps of preceding layers.

The network is trained by optimizing the AAMsoftmax loss on the speaker identities in the training corpus. The AAM-softmax is a powerful enhancement compared to the regular softmax loss in the context of fine-grained classification and verification problems. It directly optimizes the cosine distance between the speaker embeddings.

The model turned out to work amazingly well for speaker verification and speaker diarization. We found it very effective in other utterance-level classification tasks such as language-id, emotion recognition, and keyword spotting.

Please take a look into the original paper for more info

Conclusion

In this tutorial, we showed how to create an utterance-level classifier from scratch using SpeechBrain. The proposed system contains all the basic ingredients to develop a state-of-the-art system (i.e., data augmentation, feature extraction, encoding, statistical pooling, classifier, etc)

We described all the steps using a small dataset only. In a real case you have to train with much more data (see for instance our Voxceleb recipe).

Related Tutorials

YAML hyperparameter specification
Brain Class
Checkpointing
Data-io
ASR from Scratch
Speech Features
Speech Augmentation
Environmental Corruption
MultiGPU Training
Citing SpeechBrain


