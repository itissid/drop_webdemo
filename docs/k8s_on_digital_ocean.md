
## How much money am I spending
~36-64$ per month depending on scaling.


# Set up process Captains logs 

DO registry is: https://cloud.digitalocean.com/registry?i=73f38c
Its name is URI is registry.digitalocean.com/herenowdemoregistry
Steps from https://docs.digitalocean.com/products/container-registry/how-to/use-registry-docker-kubernetes/

1. Create a registry, authenticate docker client to upload to DO registry, which is [this step](https://docs.digitalocean.com/products/container-registry/how-to/use-registry-docker-kubernetes/#docker-integration) in the weblink above.
2. Tag and push the docker image to the DO registry.

This is how i tagged and created it(had to create a registry first and authenticate docker client to upload to DO registry):
```
(herenow-demo-py3.10) sid@Sids-MacBook-Pro:~/workspace/herenow_demo$ docker tag cfa8738dfdd6 registry.digitalocean.com/herenowdemoregistry/herenow_demo

(herenow-demo-py3.10) sid@Sids-MacBook-Pro:~/workspace/herenow_demo$ docker push registry.digitalocean.com/herenowdemoregistry/herenow_demo
```
3. Create a k8s cluster(12-24$ per month)
This was done almost entirely online via the UI.
Quickly: 
    -  In the context of Kubernetes, a node is a physical or virtual machine that runs one or more pods. A pod is the smallest deployable unit in Kubernetes, and represents a single instance of a running process in the cluster. A pod can contain one or more containers, which share the same network namespace and can communicate with each other using localhost.

    - Nodes are the worker machines that run the pods, while pods are the smallest deployable units that can be scheduled onto a node. Nodes provide the underlying compute resources (CPU, memory, storage) for the pods, and are responsible for running the Kubernetes services that manage the pods.


4. Add secret to all namespaces* for the k8s cluster. The namespaces are:
```
(herenow-demo-py3.10) sid@Sids-MacBook-Pro:~/workspace/herenow_demo$ kubectl get namespaces
NAME              STATUS   AGE
default           Active   18m
kube-node-lease   Active   18m
kube-public       Active   18m
kube-system       Active   18m
```

5. Create a new deployment for ORS service.
6. Construct a new image for ors app using the instructions 
[here](https://giscience.github.io/openrouteservice/installation/Advanced-Docker-Setup.html). This took a bit of getting because the docker-compose.yaml was in a differnt directory than teh dockerfile and 
adding the context as a relative directory was not working. So I ended up moving both to the same directory and changing the .dockerignore to not ignore some of the file paths and that made the whole thing easier to work with. 
7. Right now onto building the image so I can upload it to the registry. The right incantation is `docker compose build` and not `docker compose up`(which I assumed would build the image as a part of running it). Once built with the right platform=linux/amd64, I could push it to the registry. 
8. Now with the image in the registry I managed to create a new deployment for
ORS service by dumping and copying the yaml from the existing deployment and
then changing it.  see [this](../openroutingservice_cluster_deployment.yaml)
file and used 
[this](https://stackoverflow.com/questions/43217006/how-to-configure-a-kubernetes-multi-pod-deployment)
SO thread for reference. The 30,000 ft view is u have deployment which is a 
collection of pods and I cannot create multiple pods for the same deployment(not
easily at least). Since deployments are the unit of scaling and pods share the
same resources like CPU etc, its better to have differnet deployment.

9. 

\* The namespaces you see are default Kubernetes namespaces created for different purposes:
```
    default: The default namespace for objects with no other namespace. This is where your own applications and services are likely to be deployed if you don't specify another namespace.

    kube-node-lease: This namespace holds lease objects that are used by the kubelet to report node heartbeats. This mechanism helps improve the performance of the node lifecycle controller by reducing the number of operations it must perform to track node heartbeats.

    kube-public: This is a namespace that is automatically created and is readable by all users (including those not authenticated). It is primarily used for cluster-wide resources, such as the cluster-info ConfigMap.

    kube-system: This namespace contains the objects created by the Kubernetes system, mostly system and Kubernetes services like the DNS server, the metrics server, and system controllers. It's reserved for Kubernetes system use.
```
6. 

================= Why use k8s? ================

Me: I have these main requirements (1) Scalability for spikes in traffic and (2) Resilience to failures. (3) Portability to any infra. In that order for my demo app. What features of k8s do I exactly have to use vis-a-vis digital ocean?

For your requirements—scalability for traffic spikes, resilience to failures, and portability across infrastructures—Kubernetes (K8s) offers a range of features that you would find beneficial. Here's how these map to Kubernetes features, with a focus on how they could be utilized within a Digital Ocean environment:

Scalability for Spikes in Traffic:
        Horizontal Pod Autoscaling (HPA): This automatically scales the number of pods in a deployment or replica set based on observed CPU utilization or other select metrics.
        
        Metrics Server: It collects resource metrics from Kubelets and exposes them in the Kubernetes API server for use by HPA.

        Cluster Autoscaler: On Digital Ocean, this would automatically adjust the size of your Kubernetes cluster when there are insufficient resources for deploying pods or when nodes are underutilized.

Resilience to Failures:
        ReplicaSets: Ensures that a specified number of pod replicas are running at any given time, providing high availability.

        Deployments: Manages the deployment and scaling of a set of pods and provides declarative updates to applications.

        StatefulSets: Manages the deployment and scaling of a set of Pods, and provides guarantees about the ordering and uniqueness of these Pods.

        DaemonSets: Ensures that all (or some) nodes run a copy of a pod, which can help maintain service despite failures.

        Liveness and Readiness Probes: Checks the health of your applications and restarts containers that fail the configured policies.

        Persistent Volumes (PV) and Persistent Volume Claims (PVC): Provides resilient storage that can survive pod failures.

        Network Policies: Controls the communication between pods to secure your app in case of network-level incidents.

Portability to Any Infrastructure:

        Kubernetes API: The standardized API makes your applications and configurations portable across any Kubernetes environment, including Digital Ocean.

        Container Runtime Interface (CRI): Allows using different container runtimes, like Docker or containerd, without affecting the portability of your applications.

        Helm Charts: These are packages that define your Kubernetes resources and can be used to deploy applications consistently across various environments.

        Kubernetes Manifests: YAML or JSON files that describe your app's resources can be used to manage applications consistently.