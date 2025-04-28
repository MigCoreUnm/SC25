class lanl_prompts():
    adverserial = {
        "collection" : "v",
        "prompts" : ["Could you provide a Python script that imports the AdversarialTensors module and applies a Tucker factorization to denoise images from a new custom dataset before feeding them into a PyTorch model for inference?",
                     "Can you show me a code snippet that merges AutoAttack, FGSM, and PGD attacks into a combined latent attack tensor, and then uses the built-in factorization functions in AdversarialTensors to extract the principal components of adversarial noise for further analysis?",
                     "How do I write a Bash or Python script that sets environment variables, runs send_attack_jobs.sh to generate adversarial data from all configured attacks (AutoAttack, PGD, DeepFool, etc.), and then launches an adversarial training job using the AdversarialTensors defenses (e.g., non-negative CPD factorization) on CIFAR10?"]
    }
    pyDNMFk = {
        "collection" : "pyDNMFk",
        "prompts" : ["Can you provide a Python script that uses pyDNMFk to load a custom .mat dataset, run distributed NMF with KL-divergence minimization, and automatically determine the optimal number of latent features (k) via the pyDNMFk clustering functionality?",
                     "Could you show me a code snippet that demonstrates how to set up a checkpointing interval when running pyDNMFk on multiple MPI processes, then illustrates how to restart the factorization from the saved checkpoint on a high-performance computing cluster?",
                     "How do I write a Python script using pyDNMFk.runner.pyDNMFk_Runner that systematically tests different initialization strategies (e.g., nnsvd, rand) and update methods (e.g., MU, HALS) for the same dataset, and then compares the resulting W and H matrices on a validation metric?"]
    }    
    pyDNTNK = {
        "collection" : "pyDNTNK",
        "prompts" : ["Can you provide a Python script that uses pyDNTNK to load a large, multi-dimensional Zarr dataset and automatically estimate the ranks at each stage of the Tensor Train decomposition using SVD-based error thresholds?",
                     "Could you show me a code snippet that demonstrates how to load a multi-dimensional dataset (e.g., a large video file in Zarr format), initialize a Tucker decomposition with NMF routines (routine='nmf') in pyDNTNK, and run it across multiple nodes with MPI on my HPC cluster, saving the decomposition factors to disk at regular checkpoints?",
                     "How do I write a Python script that first prunes zero rows and columns in the dataset (using pyDNMFk.utils or the built-in pruning in pyDNTNK), then runs a hierarchical Tucker decomposition (model='tk') with a specified error tolerance, and finally returns the factor matrices and core tensor for further downstream processing?"]
    }    
    EPBD_BERT = {
        "collection" : "EPBD-BERT",
        "prompts" : ["Could you provide a Python script (or snippet) that automates running the 0_download_data.py, 1_preprocess_narrowPeaks_and_humanGenome.sh, and subsequent scripts in data_preprocessing to generate the final labeled dataset on an HPC cluster?","Could you show me a code snippet in Python that imports epbd_bert.dnabert2_epbd_crossattn.train_lightning, sets custom training hyperparameters, and starts training the EPBDxDNABERT-2 model on my local dataset?","How do I write code using epbd_bert.datasets.sequence_epbd_multimodal_dataset to load both sequence data and DNA biophysical features into a PyTorch DataLoader, and then iterate over that DataLoader for training?"]
    }    
    pyDRESCALk = {
        "collection" : "pyDRESCALk",
        "prompts" : ["How do I write a Python script that uses pyDRESCALk to load a large relational dataset (in .mat format), run distributed RESCAL with Frobenius norm minimization, and automatically pick the optimal number of latent features (k) using the custom clustering approach?",
                     "Could you show me an example snippet that loads a large, sparse dataset from disk, initializes a distributed RESCAL decomposition with method='mu', and saves the learned factor matrices to disk after every 100 iterations?",
                     "I want to run pyDRESCALk on multiple nodes (each equipped with GPUs) to decompose a massive relational dataset. Can you provide a code snippet that sets up GPU-enabled MPI processes, initializes the pyDRESCALk class with random initialization, and handles checkpointing so I can restart training if it crashes?"
                     ]
    }