import tensorflow as tf  
import numpy as np
from collections import namedtuple
import datetime
import ocr_utils
'''
        # To see the results in Chrome, 
        # Run the following in terminal to activate server.
        # tensorboard --logdir '/tmp/ds_logs/'
        # See results on localhost:6006 
'''
        
class network(object):
    ''' definition of the network
    '''
    def __init__(self, truthed_features, dtype=np.float32):
        self._ph=None
        self._keep_prob=None
        self._train_step =None
        self._accuracy=None   
        self._prediction=None         
        self._merged=None
        self._writer=None
        self._correct_prediction=None 


        lst = []
        extra_features_width = 0 # width of extra features
        
        """# ==============================================================================
        
        Placeholders
        
        Compute the size of various layers 
        
        Create a tensorflow Placeholder for each feature of data returned from the
        dataset
        
        """# ==============================================================================        
        
        for i,nm in enumerate(truthed_features.feature_names):
            
            # features[0], is always the target. For instance it may be m_label_one_hot 
            # the second features[1] is the 'image' that is passed to the convolution layers 
            # Any additional features bypass the convolution layers and go directly 
            # into the fully connected layer.  
            
            # The width of the extra features is calculated in order to allocate 
            # the correct widths of weights,  # and inputs 
            # names are assigned to make the look pretty on the tensorboard graph.
            
            if i == 0:
                nm = 'y_'+nm
            else:
                nm = 'x_'+nm
            if i>1:
                extra_features_width += truthed_features.feature_width[i]
            lst.append(tf.placeholder(dtype, shape=[None, truthed_features.feature_width[i]], name=nm))
            
        # ph is a named tuple with key names like 'image', 'm_label', and values that
        # are tensors.  The display name on the Chrome graph are 'y_m_label', 'x_image, 
        # x_upper_case etc.
    
    
        Place_Holders = namedtuple('Place_Holders', truthed_features.feature_names)   
        self._ph = Place_Holders(*lst) # unpack placeholders into named Tuple
        self._keep_prob = tf.placeholder(dtype,name='keep_prob')    
        self._nRows = truthed_features.num_rows #image height
        self._nCols = truthed_features.num_columns #image width    
        nFc = 1024      # size of fully connected layer
        nConv1 = 32     # size of first convolution layer
        nConv2 = 64     # size of second convolution layer
        nTarget = truthed_features.feature_width[0]  # the number of one_hot features in the target, 'm_label'    
        n_h_pool2_outputs = int(self._nRows/4) * int(self._nCols/4) * nConv2 # second pooling layer 
        n_h_pool2_outputsx = n_h_pool2_outputs + extra_features_width # fully connected
            
        """# ==============================================================================
        
        Build a Multilayer Convolutional Network
        
        Weight Initialization
        
        """# ==============================================================================
        
        def weight_variable(shape, dtype):
            initial = tf.truncated_normal(shape, stddev=0.1,dtype=dtype)
            return tf.Variable(initial)
        
        def bias_variable(shape, dtype):
            initial = tf.constant(0, shape=shape, dtype=dtype)
            return tf.Variable(initial)   
        
        """# ==============================================================================
        
        Convolution and Pooling
        
        keep our code cleaner, let's also abstract those operations into functions.
        
        """# ==============================================================================
        
        def conv2d(x, W):
            return tf.nn.conv2d(x, W, strides=[1, 1, 1, 1], padding='SAME')
        
        def max_pool_2x2(x):
            return tf.nn.max_pool(x, ksize=[1, 2, 2, 1],
                                strides=[1, 2, 2, 1], padding='SAME')
        
        """# ==============================================================================
        
        Image debugging output
        
        """# ==============================================================================  
        
        with tf.name_scope("reshape_x_image") as scope:
            self._x_image = tf.reshape(self._ph.image, [-1,self._nCols,self._nRows,1])
        
        image_summ = tf.image_summary("x_image", self._x_image)


        
        """# ==============================================================================
        
        Dropout
        
        """# ==============================================================================
        
        with tf.name_scope("drop") as scope:
            h_fc1_drop = tf.nn.dropout(h_fc1, self._keep_prob)
        
        """# ==============================================================================
        
        Readout Layer
        
        """# ==============================================================================
        with tf.name_scope("softmax") as scope:
            W_fc2 = weight_variable([nFc, nTarget],dtype)
            b_fc2 = bias_variable([nTarget],dtype)    
            y_conv=tf.nn.softmax(tf.matmul(h_fc1_drop, W_fc2) + b_fc2)
    
        
        with tf.name_scope("xent") as scope:
        
            # 1e-8 added to eliminate the crash of training when taking log of 0
            self._cross_entropy = -tf.reduce_sum(self._ph[0]*tf.log(y_conv+ 1e-8  ))
            ce_summ = tf.scalar_summary("cross entropy", self._cross_entropy)
            
        with tf.name_scope("train") as scope:
            self._train_step = tf.train.AdamOptimizer(1e-4).minimize(self._cross_entropy)
    
        with tf.name_scope("test") as scope:        
            self._correct_prediction = tf.equal(tf.argmax(y_conv,1), tf.argmax(self._ph[0],1))
            self._prediction = tf.argmax(y_conv,1)
        
            self._accuracy = tf.reduce_mean(tf.cast(self._correct_prediction, dtype))
            accuracy_summary = tf.scalar_summary("accuracy", self._accuracy)    
        """# ==============================================================================
        
        Start TensorFlow Session
        
        """# ==============================================================================          
        self._sess = tf.Session()          
        self._sess.run(tf.initialize_all_variables())  
        self._merged = tf.merge_all_summaries()
        tm = ""
        tp = datetime.datetime.now().timetuple()
        for i in range(4):
            tm += str(tp[i])+'-'
        tm += str(tp[4])    
        self._writer = tf.train.SummaryWriter("/tmp/ds_logs/"+ tm, self._sess.graph)
        
        def computeSize(s,tens):
            sumC = 1
            tShape = tens.get_shape()
            nDims = len(tShape)
            for i in range(nDims):
                sumC *= tShape[i].value
            print ('\t{}\t{}'.format(s,sumC),flush=True)
            return sumC
                
        print ('network size:',flush=True)
        total = computeSize("W_fc1",W_fc1)+ \
        computeSize ("b_fc1",b_fc1) + \
        computeSize ("W_conv1",W_conv1) + \
        computeSize ("b_conv1",b_conv1) + \
        computeSize ("W_conv2",W_conv2) + \
        computeSize ("b_conv2",b_conv2) + \
        computeSize ("W_fc2",W_fc2) + \
        computeSize ("b_fc2",b_fc2)
        print('\ttotal\t{}'.format(total),flush=True )
        

        
    def __exit__(self, exc_type, exc_value, traceback):
        tf.reset_default_graph() # only necessary when iterating through fonts
        self._sess.close()  
        
        

    def fit(self, truthed_data, nEpochs=5000):    

        perfect_count=10
        for i in range(nEpochs):
        
            batch = truthed_data.next_batch(100)
            # assign feature data to each placeholder
            # the batch list is returned in the same order as the features requested
            feed = {self._keep_prob: 0.5}
            for j in range(truthed_data.num_features):
                feed[self._ph[j]] = batch[j]  
                
            if i%100 == 0:
                # sh=h_pool2_flat.get_shape()
                feed[self._keep_prob] = 1.0
                result = self._sess.run([self._merged, self._accuracy ], feed_dict=feed)    
                summary_str = result[0]
                #acc = result[1]       
                self._writer.add_summary(summary_str, i)
                train_accuracy = result[1]  
                if train_accuracy <= (1.0 - 1e-5  ):
                    perfect_count=10;
                else:
                    perfect_count -= 1
                    if perfect_count==0:
                        break;  
                    
                print ("step %d, training accuracy %g"%(i, train_accuracy),flush=True)
            self._sess.run(self._train_step.run,feed_dict=feed)
            

    


    def test(self, truthed_features): 
        feed={self._keep_prob: 1.0}
        # assign feature data to each placeholder
        error_images = np.empty((0,self._nRows,self._nCols))
            
        test_accuracy=0
        m=0
          
        for j in range(truthed_features.num_features):
             feed[self._ph[j]] =truthed_features.features[j]
        result = self._sess.run([self._accuracy, self._x_image, self._correct_prediction], feed_dict=feed)    
        test_accuracy += result[0]
        error_images = np.append(error_images, result[1][:,:,:,0][result[2]==False],axis=0)
        m += 1
        try:        
            print ("test accuracy {} for font: {}".format(test_accuracy/m, input_filters_dict['font']),flush=True)       
            ocr_utils.montage(error_images,title='TensorFlow {} Error Images'.format(input_filters_dict['font']))  
        except:  
            if m==0:
                print ("test accuracy 1",flush=True)
            else:                                                                    
                print ("test accuracy {}".format(test_accuracy/m),flush=True)  
                ocr_utils.montage(error_images,title='TensorFlow Error Images') 
        
         
    def predict(self, truthed_features): 
        feed={self._keep_prob: 1.0}
        # assign feature data to each placeholder
        error_images = np.empty((truthed_features.num_rows,truthed_features.num_columns))
            
        test_accuracy=0
        m=0
          
        for j in range(1,truthed_features.num_features):
             feed[self._ph[j]] = truthed_features.features[j]
        result = self._sess.run([self._prediction], feed_dict=feed)    
    
        return result[0]
     
                  