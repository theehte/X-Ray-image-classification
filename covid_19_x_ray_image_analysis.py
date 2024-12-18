
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
# warnings.filterwarnings("ignore", category=MatplotlibDeprecationWarning)


# Data Reading
import os
from glob import glob
from PIL import Image
import pickle

# Data Processing
import pandas as pd
import numpy as np
import cv2
import random
from imblearn.over_sampling import RandomOverSampler
from imblearn.under_sampling import RandomUnderSampler
from sklearn.decomposition import PCA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import visualkeras

# import albumentations as A

# Data plotting
import seaborn as sns
# import plotly.express as px
import matplotlib.pyplot as plt

# Data Modeling & Model Evaluation

from sklearn.model_selection import train_test_split as tts
from keras.preprocessing import image
import tensorflow as tf
from tensorflow.keras import layers, models
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay, classification_report, recall_score, accuracy_score, precision_score, f1_score
from sklearn.metrics import confusion_matrix
from sklearn.metrics import classification_report

# Grad-CAM

import keras
import matplotlib.cm as cm

def plot_accuracy(model_history):
    plt.plot(model_history.history['accuracy'])
    plt.plot(model_history.history['val_accuracy'])
    plt.title('Model Accuracy')
    plt.ylabel('Accuracy')
    plt.xlabel('Epoch')
    plt.legend(['Train', 'Validation'], loc = 'lower right')
    plt.show()

def plot_loss(model_history):
    plt.plot(model_history.history['loss'])
    plt.plot(model_history.history['val_loss'])
    plt.title('Model Loss')
    plt.ylabel('Loss')
    plt.xlabel('Epoch')
    plt.legend(['Train', 'Validation'], loc = 'upper right')
    plt.show()

def prediction(model, test_loader):

  x_test = []
  y_test = []

  for i in range(len(test_loader)):
    batch = test_loader[i]
    for j in range(len(batch[0])):
      img = batch[0][j]
      img = np.expand_dims(img, axis = 0)
      label = batch[1][j]
      x_test.append(img)
      y_test.append(label)

  y_pred = []
  for i, img in enumerate(x_test):
    prediction = model.predict(img, verbose = 0)
    prediction = np.argmax(prediction)
    y_pred.append(prediction)

  print(f"predicted {i+1} samples")

  return np.array(y_test), np.array(y_pred)

"""**Considering Lung_Opacity and Viral Pneumonia as Normal**"""

files = ['Normal', 'COVID', 'Lung_Opacity','Viral Pneumonia']
data_dir = 'COVID_19_Radiography_Dataset'
data = []
for i, level in enumerate(files):
    local_path = os.listdir(os.path.join(data_dir, level + '/' + 'images'))
    for file in local_path:
        result_type = level
        if( level == 'Lung_Opacity' or level == 'Viral Pneumonia' ):
            result_type = 'Normal'
        data.append([level + '/' + 'images' + '/' + file , result_type])

data = pd.DataFrame(data, columns = ['image_file', 'result'])
data['path'] = data_dir + '/' + data['image_file']
data['result'] = data['result'].map({'Normal': 'Negative', 'COVID': 'Positive'})
data.head()

sns.set_theme(style = "darkgrid")
ax = sns.countplot(x = data["result"])

for p in ax.patches:
    ax.annotate(f'{p.get_height():.0f}', (p.get_x() + p.get_width() / 2., p.get_height()),
                ha='center', va='center', fontsize=11, color='black', xytext=(0, 10),
                textcoords='offset points')

sampler = RandomUnderSampler(sampling_strategy = 'majority')
# sampler = RandomOverSampler(sampling_strategy = 'minority')
x_temp = data.drop(columns = ["result"])
y_temp = data["result"]

del data

x_temp, y_temp = sampler.fit_resample(x_temp, y_temp)
data = x_temp
data["result"] = y_temp

sns.set_theme(style = "darkgrid")
ax = sns.countplot(x = data["result"])

for p in ax.patches:
    ax.annotate(f'{p.get_height():.0f}', (p.get_x() + p.get_width() / 2., p.get_height()),
                ha='center', va='center', fontsize=11, color='black', xytext=(0, 10),
                textcoords='offset points')

paths = data['path'].to_numpy()
labels = data['result'].to_numpy()

paths_train, paths_test, labels_train, labels_test = tts(paths, labels, test_size=0.2, random_state=42, shuffle = True)
paths_train, paths_val, labels_train, labels_val = tts(paths, labels, test_size=0.2, random_state=42, shuffle = True)

train_datagen = ImageDataGenerator(
    rescale=1./255,  # rescale the pixel values to [0, 1]
    rotation_range=10,  # rotate the image randomly by up to 10 degrees
    zoom_range=0.1,  # zoom in/out on the image randomly by up to 10%
    horizontal_flip=True,  # flip the image horizontally with probability 0.5
    vertical_flip=False,  # don't flip the image vertically
    fill_mode='nearest'  # fill any pixels lost during transformations with the nearest pixel
)

val_datagen = ImageDataGenerator(
    rescale=1./255,  # rescale the pixel values to [0, 1]
    rotation_range=5,  # rotate the image randomly by up to 10 degrees
    zoom_range=0.1,  # zoom in/out on the image randomly by up to 10%
)

test_datagen = ImageDataGenerator(
    rescale=1./255,  # rescale the pixel values to [0, 1]
)

def loader_gen( train_datagen, val_datagen, test_datagen, targetsize, batchsize ):

  train_loader = train_datagen.flow_from_dataframe(
      dataframe=pd.DataFrame({'path': paths_train, 'label': labels_train}),
      x_col = 'path',
      y_col = 'label',
      target_size = targetsize,
      batch_size = batchsize,
      class_mode = 'binary'
  )

  val_loader = val_datagen.flow_from_dataframe(
      dataframe=pd.DataFrame({'path': paths_val, 'label': labels_val}),
      x_col = 'path',
      y_col = 'label',
      target_size = targetsize,
      batch_size = batchsize,
      class_mode = 'binary'
  )

  test_loader = test_datagen.flow_from_dataframe(
      dataframe=pd.DataFrame({'path': paths_test, 'label': labels_test}),
      x_col = 'path',
      y_col = 'label',
      target_size = targetsize,
      batch_size = batchsize,
      class_mode = 'binary'
  )

  return train_loader, val_loader, test_loader

"""**CNN 1**"""

train_loader1, val_loader1, test_loader1 = loader_gen( train_datagen, val_datagen, test_datagen, (64,64), 40 )

model1 = models.Sequential()

model1.add(layers.Conv2D(filters = 16, kernel_size = (3,3), activation = 'relu', input_shape = (64, 64, 3)))
model1.add(layers.MaxPooling2D((2,2), strides = 2))
model1.add(layers.Dropout(0.2))

model1.add(layers.Conv2D(filters = 32, kernel_size = (3,3), activation = 'relu'))
model1.add(layers.MaxPooling2D((2,2), strides = 2))
model1.add(layers.Dropout(0.2))

model1.add(layers.Flatten())

model1.add(layers.Dense(units = 64, activation = 'relu'))

model1.add(layers.Dense(units = 32, activation = 'relu'))

model1.add(layers.Dense(units = 16, activation = 'relu'))

model1.add(layers.Dense(units = 2, activation = 'softmax'))

model1.compile(optimizer = 'adam',
           loss = tf.keras.losses.SparseCategoricalCrossentropy(from_logits = False),
           metrics = ['accuracy'])

model1.summary()

es = tf.keras.callbacks.EarlyStopping(monitor = 'val_loss', mode = 'min', verbose = 1, patience = 4)

history1 = model1.fit(train_loader1,
                         epochs = 20,
                        #  steps_per_epoch = 400,
                         validation_data = val_loader1,
                        #  validation_steps = 100,
                         callbacks = [es])

plot_accuracy(history1)

plot_loss(history1)

y_test1, y_pred1 = prediction(model1, test_loader1)

loss, acc = model1.evaluate(test_loader1)
print(f"Loss of the model is : {loss*100} %")
print(f"Accuracy of the model is : {acc*100} %")

conf_mat = confusion_matrix(y_pred1, y_test1)
sns.heatmap(conf_mat, annot = True,  fmt='g', annot_kws={"size": 14})
print(classification_report(y_pred1, y_test1))

visualkeras.layered_view(model1)

"""**CNN 2**"""

train_loader2, val_loader2, test_loader2 = loader_gen( train_datagen, val_datagen, test_datagen, (64,64), 40 )

model2 = models.Sequential()

model2.add(layers.Conv2D(filters = 16, kernel_size = (3,3), activation = 'relu', input_shape = (64, 64, 3)))
model2.add(layers.MaxPooling2D((2,2), strides = 2))
model2.add(layers.Dropout(0.2))

model2.add(layers.Conv2D(filters = 32, kernel_size = (3,3), activation = 'relu'))
model2.add(layers.MaxPooling2D((2,2), strides = 2))
model2.add(layers.Dropout(0.2))

model2.add(layers.Conv2D(filters = 64, kernel_size = (3,3), activation = 'relu'))
model2.add(layers.MaxPooling2D((2,2), strides = 2))
model2.add(layers.Dropout(0.2))

model2.add(layers.Flatten())

model2.add(layers.Dense(units = 32, activation = 'relu'))

model2.add(layers.Dense(units = 16, activation = 'relu'))

model2.add(layers.Dense(units = 2, activation = 'softmax'))

model2.compile(optimizer = 'adam',
           loss = tf.keras.losses.SparseCategoricalCrossentropy(from_logits = False),
           metrics = ['accuracy'])

model2.summary()

es = tf.keras.callbacks.EarlyStopping(monitor = 'val_loss', mode = 'min', verbose = 1, patience = 4)

history2 = model2.fit(train_loader2,
                         epochs = 20,
                        #  steps_per_epoch = 400,
                         validation_data = val_loader2,
                        #  validation_steps = 100,
                         callbacks = [es])

plot_accuracy(history2)

plot_loss(history2)

y_test2, y_pred2 = prediction(model2, test_loader2)

loss, acc = model2.evaluate(test_loader2)
print(f"Loss of the model is : {loss*100} %")
print(f"Accuracy of the model is : {acc*100} %")

conf_mat = confusion_matrix(y_pred2, y_test2)
sns.heatmap(conf_mat, annot = True,  fmt='g', annot_kws={"size": 14})
print(classification_report(y_pred2, y_test2))

visualkeras.layered_view(model2)

"""**Not considering Lung_Opacity and Viral Pneumonia**"""

files = ['Normal', 'COVID']
data_dir = 'COVID_19_Radiography_Dataset'
data = []
for i, level in enumerate(files):
    local_path = os.listdir(os.path.join(data_dir, level + '/' + 'images'))
    for file in local_path:
        result_type = level
        if( level == 'Lung_Opacity' or level == 'Viral Pneumonia' ):
            result_type = 'Normal'
        data.append([level + '/' + 'images' + '/' + file , result_type])

data = pd.DataFrame(data, columns = ['image_file', 'result'])
data['path'] = data_dir + '/' + data['image_file']
data['result'] = data['result'].map({'Normal': 'Negative', 'COVID': 'Positive'})
data.head()

paths = data['path'].to_numpy()
labels = data['result'].to_numpy()

paths_train, paths_test, labels_train, labels_test = tts(paths, labels, test_size=0.2, random_state=42, shuffle = True)
paths_train, paths_val, labels_train, labels_val = tts(paths, labels, test_size=0.2, random_state=42, shuffle = True)

train_datagen = ImageDataGenerator(
    rescale=1./255,  # rescale the pixel values to [0, 1]
    rotation_range=10,  # rotate the image randomly by up to 10 degrees
    zoom_range=0.1,  # zoom in/out on the image randomly by up to 10%
    horizontal_flip=True,  # flip the image horizontally with probability 0.5
    vertical_flip=False,  # don't flip the image vertically
    fill_mode='nearest'  # fill any pixels lost during transformations with the nearest pixel
)

val_datagen = ImageDataGenerator(
    rescale=1./255,  # rescale the pixel values to [0, 1]
    rotation_range=5,  # rotate the image randomly by up to 10 degrees
    zoom_range=0.1,  # zoom in/out on the image randomly by up to 10%
)

test_datagen = ImageDataGenerator(
    rescale=1./255,  # rescale the pixel values to [0, 1]
)

def loader_gen( train_datagen, val_datagen, test_datagen, targetsize, batchsize ):

  train_loader = train_datagen.flow_from_dataframe(
      dataframe=pd.DataFrame({'path': paths_train, 'label': labels_train}),
      x_col = 'path',
      y_col = 'label',
      target_size = targetsize,
      batch_size = batchsize,
      class_mode = 'binary'
  )

  val_loader = val_datagen.flow_from_dataframe(
      dataframe=pd.DataFrame({'path': paths_val, 'label': labels_val}),
      x_col = 'path',
      y_col = 'label',
      target_size = targetsize,
      batch_size = batchsize,
      class_mode = 'binary'
  )

  test_loader = test_datagen.flow_from_dataframe(
      dataframe=pd.DataFrame({'path': paths_test, 'label': labels_test}),
      x_col = 'path',
      y_col = 'label',
      target_size = targetsize,
      batch_size = batchsize,
      class_mode = 'binary'
  )

  return train_loader, val_loader, test_loader

"""**CNN 1**"""

train_loader1_2, val_loader1_2, test_loader1_2 = loader_gen( train_datagen, val_datagen, test_datagen, (64,64), 40 )

model1_2 = models.Sequential()

model1_2.add(layers.Conv2D(filters = 16, kernel_size = (3,3), activation = 'relu', input_shape = (64, 64, 3)))
model1_2.add(layers.MaxPooling2D((2,2), strides = 2))
model1_2.add(layers.Dropout(0.2))

model1_2.add(layers.Conv2D(filters = 32, kernel_size = (3,3), activation = 'relu'))
model1_2.add(layers.MaxPooling2D((2,2), strides = 2))
model1_2.add(layers.Dropout(0.2))

model1_2.add(layers.Flatten())

model1_2.add(layers.Dense(units = 64, activation = 'relu'))

model1_2.add(layers.Dense(units = 32, activation = 'relu'))

model1_2.add(layers.Dense(units = 16, activation = 'relu'))

model1_2.add(layers.Dense(units = 2, activation = 'softmax'))

model1_2.compile(optimizer = 'adam',
           loss = tf.keras.losses.SparseCategoricalCrossentropy(from_logits = False),
           metrics = ['accuracy'])

model1_2.summary()

es = tf.keras.callbacks.EarlyStopping(monitor = 'val_loss', mode = 'min', verbose = 1, patience = 4)

history1_2 = model1_2.fit(train_loader1_2,
                         epochs = 20,
                         validation_data = val_loader1_2,
                         callbacks = [es])

plot_accuracy(history1_2)

plot_loss(history1_2)

y_test1_2, y_pred1_2 = prediction(model1_2, test_loader1_2)

loss, acc = model1_2.evaluate(test_loader1_2)
print(f"Loss of the model is : {loss*100} %")
print(f"Accuracy of the model is : {acc*100} %")

conf_mat = confusion_matrix(y_pred1_2, y_test1_2)
sns.heatmap(conf_mat, annot = True,  fmt='g', annot_kws={"size": 14})
print(classification_report(y_pred1_2, y_test1_2))

visualkeras.layered_view(model1_2)

"""**CNN 2**"""

train_loader2_2, val_loader2_2, test_loader2_2 = loader_gen( train_datagen, val_datagen, test_datagen, (64,64), 40 )

model2_2 = models.Sequential()

model2_2.add(layers.Conv2D(filters = 16, kernel_size = (3,3), activation = 'relu', input_shape = (64, 64, 3)))
model2_2.add(layers.MaxPooling2D((2,2), strides = 2))
model2_2.add(layers.Dropout(0.2))

model2_2.add(layers.Conv2D(filters = 32, kernel_size = (3,3), activation = 'relu'))
model2_2.add(layers.MaxPooling2D((2,2), strides = 2))
model2_2.add(layers.Dropout(0.2))

model2_2.add(layers.Conv2D(filters = 64, kernel_size = (3,3), activation = 'relu'))
model2_2.add(layers.MaxPooling2D((2,2), strides = 2))
model2_2.add(layers.Dropout(0.2))

model2_2.add(layers.Flatten())

model2_2.add(layers.Dense(units = 32, activation = 'relu'))

model2_2.add(layers.Dense(units = 16, activation = 'relu'))

model2_2.add(layers.Dense(units = 2, activation = 'softmax'))

model2_2.compile(optimizer = 'adam',
           loss = tf.keras.losses.SparseCategoricalCrossentropy(from_logits = False),
           metrics = ['accuracy'])

model2_2.summary()

es = tf.keras.callbacks.EarlyStopping(monitor = 'val_loss', mode = 'min', verbose = 1, patience = 4)

history2_2 = model2_2.fit(train_loader2_2,
                         epochs = 20,
                         validation_data = val_loader2_2,
                         callbacks = [es])

plot_accuracy(history2_2)

plot_loss(history2_2)

y_test2_2, y_pred2_2 = prediction(model2_2, test_loader2_2)

loss, acc = model2_2.evaluate(test_loader2_2)
print(f"Loss of the model is : {loss*100} %")
print(f"Accuracy of the model is : {acc*100} %")

conf_mat = confusion_matrix(y_pred2_2, y_test2_2)
sns.heatmap(conf_mat, annot = True,  fmt='g', annot_kws={"size": 14})
print(classification_report(y_pred2_2, y_test2_2))

visualkeras.layered_view(model2_2)

def image_prediction(test_image, model, img_num):
    plt.imshow(test_image[img_num], cmap = 'gray')
    img = np.expand_dims(test_image[img_num], axis = 0)
    image_prediction = np.argmax(model.predict(img, verbose = 'False'))

    img_prediction = ''
    if image_prediction == 0:
        img_prediction = "Negative"
    else:
        img_prediction = "Positive"

    plt.title(img_prediction, fontsize = 14)

    return img_prediction

test_img = test_loader2_2[0][0]
image_prediction(test_img, model1_2, 3);
