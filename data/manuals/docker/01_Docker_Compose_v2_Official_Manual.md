# Docker Compose v2 Official Manual
Generated: Fri Sep  4 12:21:23 AM UTC 2026


---
## File: customize.md

---
title: Customize Compose Bridge 
linkTitle: Customize
weight: 20
description: Learn how to customize Compose Bridge transformations using Go templates and Compose extensions
keywords: docker compose bridge, customize compose bridge, compose bridge templates, compose to kubernetes, compose bridge transformation, go templates docker
---

{{< summary-bar feature_name="Compose bridge" >}}

You can customize how Compose Bridge converts your Docker Compose files into platform-specific formats. 

This page explains how Compose Bridge uses templating to generate Kubernetes manifests and how you can customize these templates for your specific requirements and needs, or how you can build your own transformation.  

## How it works 

Compose bridge uses transformations to let you convert a Compose model into another form. 

A transformation is packaged as a Docker image that receives the fully-resolved Compose model as `/in/compose.yaml` and can produce any target format file under `/out`.

Compose Bridge includes a default Kubernetes transformation using Go templates, which you can customize by replacing or extending templates.

### Template syntax

Compose Bridge makes use of templates to transform a Compose configuration file into Kubernetes manifests. Templates are plain text files that use the [Go templating syntax](https://pkg.go.dev/text/template). This enables the insertion of logic and data, making the templates dynamic and adaptable according to the Compose model.

When a template is executed, it must produce a YAML file which is the standard format for Kubernetes manifests. Multiple files can be generated as long as they are separated by `---`

Each YAML output file begins with custom header notation, for example:

```yaml
#! manifest.yaml
```

In the following example, a template iterates over services defined in a `compose.yaml` file. For each service, a dedicated Kubernetes manifest file is generated, named according to the service and containing specified configurations.

```yaml
{{ range $name, $service := .services }}
---
#! {{ $name }}-manifest.yaml
# Generated code, do not edit
key: value
## ...
{{ end }}
```

### Input model

You can generate the input model by running `docker compose config`. 

This canonical YAML output serves as the input for Compose Bridge transformations. Within the templates, data from the `compose.yaml` is accessed using dot notation, allowing you to navigate through nested data structures. For example, to access the deployment mode of a service, you would use `service.deploy.mode`:

 ```yaml
# iterate over a yaml sequence
{{ range $name, $service := .services }}
  # access a nested attribute using dot notation
  {{ if eq $service.deploy.mode "global" }}
kind: DaemonSet
  {{ end }}
{{ end }}
```

You can check the [Compose Specification JSON schema](https://github.com/compose-spec/compose-go/blob/main/schema/compose-spec.json) for a full overview of the Compose model. This schema outlines all possible configurations and their data types in the Compose model. 

### Helper functions

As part of the Go templating syntax, Compose Bridge offers a set of YAML helper functions designed to manipulate data within the templates efficiently:

| Function    | Description                                                                                                 |
| ----------- | ----------------------------------------------------------------------------------------------------------- |
| `seconds`   | Converts a [duration](/reference/compose-file/extension.md#specifying-durations) into an integer (seconds). |
| `uppercase` | Converts a string to uppercase.                                                                             |
| `title`     | Capitalizes the first letter of each word.                                                                  |
| `safe`      | Converts a string into a safe identifier (replaces non-lowercase characters with `-`).                      |
| `truncate`  | Removes the first N elements from a list.                                                                   |
| `join`      | Joins list elements into a single string with a separator.                                                  |
| `base64`    | Encodes a string as base64 (used for Kubernetes secrets).                                                   |
| `map`       | Maps values using `“value -> newValue”` syntax.                                                             |
| `indent`    | Indents string content by N spaces.                                                                         |
| `helmValue` | Outputs a Helm-style template value.                                                                        |

In the following example, the template checks if a healthcheck interval is specified for a service, applies the `seconds` function to convert this interval into seconds and assigns the value to the `periodSeconds` attribute.

```yaml
{{ if $service.healthcheck.interval }}
            periodSeconds: {{ $service.healthcheck.interval | seconds }}{{ end }}
{{ end }}
```

## Customize the default templates

As Kubernetes is a versatile platform, there are many ways
to map Compose concepts into Kubernetes resource definitions. Compose
Bridge lets you customize the transformation to match your own infrastructure
decisions and preferences, with varying level of flexibility and effort.

### Modify the default templates

You can extract templates used by the default transformation `docker/compose-bridge-kubernetes`:

```console
$ docker compose bridge transformations create --from docker/compose-bridge-kubernetes my-template
``` 

The templates are extracted into a directory named after your template name, in this case `my-template`. It includes:

- A Dockerfile that lets you create your own image to distribute your template
- A directory containing the templating files

Edit, [add](#add-your-own-templates), or remove templates as needed. 

You can then use the generated Dockerfile to package your changes into a new transformation image, which you can then use with Compose Bridge:

```console
$ docker build --tag mycompany/transform --push .
```

Use your transformation as a replacement:

```console
$ docker compose bridge convert --transformations mycompany/transform 
```

#### Model Runner templates

The default transformation also includes templates for applications that use LLMs:

- `model-runner-deployment.tmpl`: Generates the Kubernetes deployment for Docker Model Runner. Customize it to change replica counts, image tags, resource requests and limits, GPU scheduling settings, tolerations, or additional environment variables.
- `model-runner-service.tmpl`: Builds the service that exposes Docker Model Runner. Update it to switch between `ClusterIP`, `NodePort`, or `LoadBalancer` types, adjust ports, or add annotations for ingress and service meshes.
- `model-runner-pvc.tmpl`: Defines the persistent volume claim used to store downloaded models. Edit it to set storage size, storage class, access modes, or volume annotations required by your storage provider.
- `/overlays/model-runner/kustomization.yaml`: Kustomize overlay applied when you deploy Model Runner to a standalone Kubernetes cluster. Extend it to add patches for labels and annotations, attach `NetworkPolicies`, or include extra manifests.
- `/overlays/desktop/deployment.tmpl`: Desktop-specific deployment template that keeps the in-cluster Model Runner scaled down and points workloads to the host endpoint. Adjust it if you change the Desktop endpoint or want to deploy Model Runner on Desktop instead of relying on the host service.

Common customization scenarios:

- Enable GPU support by adding vendor-specific resource requests, limits, and node selectors in `model-runner-deployment.tmpl`.
- Increase or tune storage for model artifacts by editing `model-runner-pvc.tmpl` to set the desired size, storage class, or access mode.
- Expose Model Runner outside the cluster by switching the service type in `model-runner-service.tmpl` or adding ingress annotations in the model-runner overlay.
- Align cluster policies by adding labels, annotations, or NetworkPolicies through `/overlays/model-runner/kustomization.yaml`.

For more details, see [Use Model Runner](use-model-runner.md).

### Add your own templates

For resources that are not managed by Compose Bridge's default transformation, 
you can build your own templates. 

The `compose.yaml` model may not offer all 
the configuration attributes required to populate the target manifest. If this is the case, you can
then rely on Compose custom extensions to better describe the
application, and offer an agnostic transformation.

For example, if you add `x-virtual-host` metadata
to service definitions in the `compose.yaml` file, you can use the following custom attribute
to produce Ingress rules:

```yaml
{{ $project := .name }}
#! {{ $name }}-ingress.yaml
# Generated code, do not edit
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: virtual-host-ingress
  namespace: {{ $project }}
spec:
  rules:  
{{ range $name, $service := .services }}
{{ range index $service "x-virtual-host" }}
  - host: ${{ . }}
    http:
      paths:
      - path: "/"
        backend:
          service:
            name: ${{ name }}
            port:
              number: 80  
{{ end }}
{{ end }}
```

Once packaged into a Docker image, you can use this custom template
when transforming Compose models into Kubernetes in addition to other
transformations:

```console
$ docker compose bridge convert \
    --transformation docker/compose-bridge-kubernetes \
    --transformation mycompany/transform 
```

### Build your own transformation

While Compose Bridge templates make it easy to customize with minimal changes,
you may want to make significant changes, or rely on an existing conversion tool.

A Compose Bridge transformation is a Docker image that is designed to get a Compose model
from `/in/compose.yaml` and produce platform manifests under `/out`. This simple 
contract makes it easy to bundle an alternate transformation using 
[Kompose](https://kompose.io/):

```Dockerfile
FROM alpine

# Get kompose from github release page
RUN apk add --no-cache curl
ARG VERSION=1.32.0
RUN ARCH=$(uname -m | sed 's/armv7l/arm/g' | sed 's/aarch64/arm64/g' | sed 's/x86_64/amd64/g') && \
    curl -fsL \
    "https://github.com/kubernetes/kompose/releases/download/v${VERSION}/kompose-linux-${ARCH}" \
    -o /usr/bin/kompose
RUN chmod +x /usr/bin/kompose

CMD ["/usr/bin/kompose", "convert", "-f", "/in/compose.yaml", "--out", "/out"]
```

This Dockerfile bundles Kompose and defines the command to run this tool according
to the Compose Bridge transformation contract.


---
## File: _index.md

---
description: Learn how Compose Bridge transforms Docker Compose files into Kubernetes manifests for seamless platform transitions
keywords: docker compose bridge, compose to kubernetes, docker compose kubernetes integration, docker compose kustomize, compose bridge docker desktop
title: Overview of Compose Bridge
linkTitle: Compose Bridge
weight: 50
---

{{< summary-bar feature_name="Compose bridge" >}}

Compose Bridge converts your Docker Compose configuration into platform-specific deployment formats such as Kubernetes manifests. By default, it generates:

- Kubernetes manifests 
- A Kustomize overlay

These outputs are ready for deployment on Docker Desktop with [Kubernetes enabled](/manuals/desktop/settings-and-maintenance/settings.md#kubernetes).  

Compose Bridge helps you bridge the gap between Compose and Kubernetes, making it easier to adopt Kubernetes while keeping the simplicity and efficiency of Compose.

It's a flexible tool that lets you either take advantage of the [default transformation](usage.md) or [create a custom transformation](customize.md) to suit specific project needs and requirements. 

## How it works

Compose Bridge uses transformations to convert a Compose model into another form. 

A transformation is packaged as a Docker image that receives the fully resolved Compose model as `/in/compose.yaml` and can produce any target format file under `/out`.

Compose Bridge provides its own transformation for Kubernetes using Go templates, so that it is easy to extend for customization by replacing or appending your own templates.

For more detailed information on how these transformations work and how you can customize them for your projects, see [Customize](customize.md).

Compose Bridge also supports applications that use LLMs via Docker Model Runner.

For more details, see [Use Model Runner](use-model-runner.md).

## Apply organizational standards at scale 


Compose Bridge supports custom transformation templates, which lets platform teams encode
organizational standards once and apply them consistently whenever a `compose.yaml` file
is converted to Kubernetes manifests or other formats.

Developers continue to write standard Compose files. During conversion, Compose Bridge
runs your custom transformation and automatically injects the required security contexts,
resource limits, labels, and network policies into the output manifests — without
requiring developers to know or manage those details.

When your requirements change, update the transformation template in one place. Every team
picks up the changes on their next conversion, with no edits to individual Compose files.

This separation of concerns keeps developers focused on application configuration, while
platform teams control governance and enforce policy through the transformation layer.

To get started, see [Customize Compose Bridge](/manuals/compose/bridge/customize.md).

## What's next?

- [Use Compose Bridge](usage.md)
- [Explore how you can customize Compose Bridge](customize.md)


---
## File: usage.md

---
title: Use the default Compose Bridge transformation
linkTitle: Usage
weight: 10
description: Learn how to use the default Compose Bridge transformation to convert Compose files into Kubernetes manifests
keywords: docker compose bridge, compose kubernetes transform, kubernetes from compose, compose bridge convert, compose.yaml to kubernetes
---

{{< summary-bar feature_name="Compose bridge" >}}

Compose Bridge includes a built-in transformation that automatically converts your Compose configuration into a set of Kubernetes manifests.

Based on your `compose.yaml` file, it produces:

- A [Namespace](https://kubernetes.io/docs/concepts/overview/working-with-objects/namespaces/) so all your resources are isolated and don't conflict with resources from other deployments.
- A [ConfigMap](https://kubernetes.io/docs/concepts/configuration/configmap/) with an entry for each and every [config](/reference/compose-file/configs.md) resource in your Compose application.
- [Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) for application services. This ensures that the specified number of instances of your application are maintained in the Kubernetes cluster.
- [Services](https://kubernetes.io/docs/concepts/services-networking/service/) for ports exposed by your services, used for service-to-service communication.
- [Services](https://kubernetes.io/docs/concepts/services-networking/service/) for ports published by your services, with type `LoadBalancer` so that Docker Desktop will also expose the same port on the host.
- [Network policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/) to replicate the networking topology defined in your `compose.yaml` file. 
- [PersistentVolumeClaims](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) for your volumes, using `hostpath` storage class so that Docker Desktop manages volume creation.
- [Secrets](https://kubernetes.io/docs/concepts/configuration/secret/) with your secret encoded. This is designed for local use in a testing environment.

It also supplies a Kustomize overlay dedicated to Docker Desktop with:
 - `Loadbalancer` for services which need to expose ports on host.
 - A `PersistentVolumeClaim` to use the Docker Desktop storage provisioner `desktop-storage-provisioner` to handle volume provisioning more effectively.
 - A `Kustomization.yaml` file to link all the resources together.

If your Compose file defines a `models` section for a service, Compose Bridge automatically configures your deployment so your service can locate and use its models via Docker Model Runner.

For each declared model, the transformation injects two environment variables:

- `<MODELNAME>_URL`: The endpoint for Docker Model Runner serving that model  
- `<MODELNAME>_MODEL`: The model’s name or identifier

You can optionally customize these variable names using `endpoint_var` and `model_var`.

The default transformation generates two different overlays - one for Docker Desktop whilst using a local instance of Docker Model Runner, and a `model-runner` overlay with all the relevant Kubernetes resources to deploy Docker Model Runner in a pod. 

| Environment    | Endpoint                                        |
| -------------- | ----------------------------------------------- |
| Docker Desktop | `http://host.docker.internal:12434/engines/v1/` |
| Kubernetes     | `http://model-runner/engines/v1/`               |


For more details, see [Use Model Runner](use-model-runner.md).

## Use the default Compose Bridge transformation

To convert your Compose file using the default transformation:

```console
$ docker compose bridge convert
```

Compose looks for a `compose.yaml` file inside the current directory and generates Kubernetes manifests.

Example output:

```console
$ docker compose -f compose.yaml bridge convert
Kubernetes resource backend-deployment.yaml created
Kubernetes resource frontend-deployment.yaml created
Kubernetes resource backend-expose.yaml created
Kubernetes resource frontend-expose.yaml created
Kubernetes resource 0-my-project-namespace.yaml created
Kubernetes resource default-network-policy.yaml created
Kubernetes resource backend-service.yaml created
Kubernetes resource frontend-service.yaml created
Kubernetes resource kustomization.yaml created
Kubernetes resource backend-deployment.yaml created
Kubernetes resource frontend-deployment.yaml created
Kubernetes resource backend-service.yaml created
Kubernetes resource frontend-service.yaml created
Kubernetes resource kustomization.yaml created
Kubernetes resource model-runner-configmap.yaml created
Kubernetes resource model-runner-deployment.yaml created
Kubernetes resource model-runner-service.yaml created
Kubernetes resource model-runner-volume-claim.yaml created
Kubernetes resource kustomization.yaml created
```

All generated files are stored in the `/out` directory in your project.

## Deploy the generated manifests

> [!IMPORTANT]
>
> Before you deploy your Compose Bridge transformations, make sure you have [enabled Kubernetes](/manuals/desktop/settings-and-maintenance/settings.md#kubernetes) in Docker Desktop.

Once the manifests are generated, deploy them to your local Kubernetes cluster:

```console
$ kubectl apply -k out/overlays/desktop/
```

> [!TIP]
>
> You can convert and deploy your Compose project to a Kubernetes cluster from the Compose file viewer.
> 
> Make sure you are signed in to your Docker account, navigate to your container in the **Containers** view, and in the top-right corner select **View configurations** and then **Convert and Deploy to Kubernetes**. 

## Additional commands

Convert a `compose.yaml` file located in another directory:

```console
$ docker compose -f <path-to-file>/compose.yaml bridge convert
```

To see all available flags, run:

```console
$ docker compose bridge convert --help
```

## What's next?

- [Explore how you can customize Compose Bridge](customize.md)
- [Use Model Runner](use-model-runner.md).

---
## File: use-model-runner.md

---
title: Use Docker Model Runner with Compose Bridge 
linkTitle: Use Model Runner
weight: 30
description: How to use Docker Model Runner with Compose Bridge for consistent deployments
keywords: docker compose bridge, customize compose bridge, compose bridge templates, compose to kubernetes, compose bridge transformation, go templates docker, model runner, ai, llms
---

Compose Bridge supports model-aware deployments. It can deploy and configure Docker Model Runner, a lightweight service that hosts and serves machine LLMs.

This reduces manual setup for LLM-enabled services and keeps deployments consistent across Docker Desktop and Kubernetes environments.

If you have a `models` top-level element in your `compose.yaml` file, Compose Bridge:

- Automatically injects environment variables for each model’s endpoint and name.
- Configures model endpoints differently for Docker Desktop vs Kubernetes.
- Optionally deploys Docker Model Runner in Kubernetes when enabled in Helm values

## Configure model runner settings

When deploying using generated Helm Charts, you can control the model runner configuration through Helm values.

```yaml
# Model Runner settings
modelRunner:
    # Set to false for Docker Desktop (uses host instance)
    # Set to true for standalone Kubernetes clusters
    enabled: false
    # Endpoint used when enabled=false (Docker Desktop)
    hostEndpoint: "http://host.docker.internal:12434/engines/v1/"
    # Deployment settings when enabled=true
    image: "docker/model-runner:latest"
    imagePullPolicy: "IfNotPresent"
    # GPU support
    gpu:
        enabled: false
        vendor: "nvidia" # nvidia or amd
        count: 1
    # Node scheduling (uncomment and customize as needed)
    # nodeSelector:
    #   accelerator: nvidia-tesla-t4
    # tolerations: []
    # affinity: {}

    # Security context
    securityContext:
        allowPrivilegeEscalation: false
    # Environment variables (uncomment and add as needed)
    # env:
    #   DMR_ORIGINS: "http://localhost:31246"
    resources:
        limits:
            cpu: "1000m"
            memory: "2Gi"
        requests:
            cpu: "100m"
            memory: "256Mi"
    # Storage for models
    storage:
        size: "100Gi"
        storageClass: "" # Empty uses default storage class
    # Models to pre-pull
    models:
        - ai/qwen2.5:latest
        - ai/mxbai-embed-large
```

## Deploying a model runner

### Docker Desktop

When `modelRunner.enabled` is `false`, Compose Bridge configures your workloads to connect to Docker Model Runner running on the host:

```text
http://host.docker.internal:12434/engines/v1/
```

The endpoint is automatically injected into your service containers.

### Kubernetes

When `modelRunner.enabled` is `true`, Compose Bridge uses the generated manifests to deploy Docker Model Runner in your cluster, including:

- Deployment: Runs the `docker-model-runner` container
- Service: Exposes port `80` (maps to container port `12434`)
- `PersistentVolumeClaim`: Stores model files

The `modelRunner.enabled` setting also determines the number of replicas for the in-cluster `model-runner-deployment`:

- When `true`, the Kubernetes deployment replica count is set to 1, and Docker Model Runner is deployed in the cluster.
- When `false`, the Kubernetes deployment replica count is 0 (no in-cluster Model Runner). On Docker Desktop, workloads still connect to the host Model Runner as described above.

---
## File: compose-sdk.md

---
description: Integrate Docker Compose directly into your applications with the Compose SDK.
keywords: docker compose sdk, compose api, Docker developer SDK
title: Using the Compose SDK
linkTitle: Compose SDK 
weight: 60
---

{{< summary-bar feature_name="Compose SDK" >}}

The `docker/compose` package can be used as a Go library by third-party applications to programmatically manage
containerized applications defined in Compose files. This SDK provides a comprehensive API that lets you
integrate Compose functionality directly into your applications, allowing you to load, validate, and manage
multi-container environments without relying on the Compose CLI. 

Whether you need to orchestrate containers as part of
a deployment pipeline, build custom management tools, or embed container orchestration into your application, the
Compose SDK offers the same powerful capabilities that drive the Docker Compose command-line tool.

## Set up the SDK

To get started, create an SDK instance using the `NewComposeService()` function, which initializes a service with the
necessary configuration to interact with the Docker daemon and manage Compose projects. This service instance provides
methods for all core Compose operations including creating, starting, stopping, and removing containers, as well as
loading and validating Compose files. The service handles the underlying Docker API interactions and resource
management, allowing you to focus on your application logic.

### Requirements

Before using the SDK, make sure you're using a compatible version of the Docker CLI. 

```go
require (
    github.com/docker/cli v28.5.2+incompatible
)
```

Docker CLI version 29.0.0 and later depends on the new `github.com/moby/moby` module, whereas Docker Compose v5 currently depends on `github.com/docker/docker`. This means you need to pin `docker/cli v28.5.2+incompatible` to ensure compatibility and avoid build errors.

### Example usage

Here's a basic example demonstrating how to load a Compose project and start the services:

```go
package main

import (
    "context"
    "log"

	"github.com/docker/cli/cli/command"
	"github.com/docker/cli/cli/flags"
    "github.com/docker/compose/v5/pkg/api"
    "github.com/docker/compose/v5/pkg/compose"
)

func main() {
    ctx := context.Background()

	dockerCLI, err := command.NewDockerCli()
	if err != nil {
		log.Fatalf("Failed to create docker CLI: %v", err)
	}
	err = dockerCLI.Initialize(&flags.ClientOptions{})
	if err != nil {
		log.Fatalf("Failed to initialize docker CLI: %v", err)
	}
	
    // Create a new Compose service instance
    service, err := compose.NewComposeService(dockerCLI)
    if err != nil {
        log.Fatalf("Failed to create compose service: %v", err)
    }

    // Load the Compose project from a compose file
    project, err := service.LoadProject(ctx, api.ProjectLoadOptions{
        ConfigPaths: []string{"compose.yaml"},
        ProjectName: "my-app",
    })
    if err != nil {
        log.Fatalf("Failed to load project: %v", err)
    }

    // Start the services defined in the Compose file
    err = service.Up(ctx, project, api.UpOptions{
        Create: api.CreateOptions{},
        Start:  api.StartOptions{},
    })
    if err != nil {
        log.Fatalf("Failed to start services: %v", err)
    }

    log.Printf("Successfully started project: %s", project.Name)
}
```

This example demonstrates the core workflow - creating a service instance, loading a project from a Compose file, and
starting the services. The SDK provides many additional operations for managing the lifecycle of your containerized
application.

## Customizing the SDK

The `NewComposeService()` function accepts optional `compose.Option` parameters to customize the SDK behavior. These
options allow you to configure I/O streams, concurrency limits, dry-run mode, and other advanced features.

```go
    // Create a custom output buffer to capture logs
    var outputBuffer bytes.Buffer

    // Create a compose service with custom options
    service, err := compose.NewComposeService(dockerCLI,
        compose.WithOutputStream(&outputBuffer),          // Redirect output to custom writer
        compose.WithErrorStream(os.Stderr),               // Use stderr for errors
        compose.WithMaxConcurrency(4),                    // Limit concurrent operations
        compose.WithPrompt(compose.AlwaysOkPrompt()),     // Auto-confirm all prompts
    )
```

### Available options

- `WithOutputStream(io.Writer)`: Redirect standard output to a custom writer
- `WithErrorStream(io.Writer)`: Redirect error output to a custom writer
- `WithInputStream(io.Reader)`: Provide a custom input stream for interactive prompts
- `WithStreams(out, err, in)`: Set all I/O streams at once
- `WithMaxConcurrency(int)`: Limit the number of concurrent operations against the Docker API
- `WithPrompt(Prompt)`: Customize user confirmation behavior (use `AlwaysOkPrompt()` for non-interactive mode)
- `WithDryRun`: Run operations in dry-run mode without actually applying changes
- `WithContextInfo(api.ContextInfo)`: Set custom Docker context information
- `WithProxyConfig(map[string]string)`: Configure HTTP proxy settings for builds
- `WithEventProcessor(progress.EventProcessor)`: Receive progress events and operation notifications

These options provide fine-grained control over the SDK's behavior, making it suitable for various integration
scenarios including CLI tools, web services, automation scripts, and testing environments.

## Tracking operations with `EventProcessor`

The `EventProcessor` interface allows you to monitor Compose operations in real-time by receiving events about changes
applied to Docker resources such as images, containers, volumes, and networks. This is particularly useful for building
user interfaces, logging systems, or monitoring tools that need to track the progress of Compose operations.

### Understanding `EventProcessor`

A Compose operation, such as `up`, `down`, `build`, performs a series of changes to Docker resources. The
`EventProcessor` receives notifications about these changes through three key methods:

- `Start(ctx, operation)`: Called when a Compose operation begins, for example `up`
- `On(events...)`: Called with progress events for individual resource changes, for example, container starting, image
  being pulled
- `Done(operation, success)`: Called when the operation completes, indicating success or failure

Each event contains information about the resource being modified, its current status, and progress indicators when
applicable (such as download progress for image pulls).

### Event status types

Events report resource changes with the following status types:

- Working: Operation is in progress, for example, creating, starting, pulling
- Done: Operation completed successfully
- Warning: Operation completed with warnings
- Error: Operation failed

Common status text values include: `Creating`, `Created`, `Starting`, `Started`, `Running`, `Stopping`, `Stopped`,
`Removing`, `Removed`, `Building`, `Built`, `Pulling`, `Pulled`, and more.

### Built-in `EventProcessor` implementations

The SDK provides three ready-to-use `EventProcessor` implementations:

- `progress.NewTTYWriter(io.Writer)`: Renders an interactive terminal UI with progress bars and task lists
  (similar to the Docker Compose CLI output)
- `progress.NewPlainWriter(io.Writer)`: Outputs simple text-based progress messages suitable for non-interactive
  environments or log files
- `progress.NewJSONWriter()`: Render events as JSON objects
- `progress.NewQuietWriter()`: (Default) Silently processes events without producing any output

Using `EventProcessor`, a custom UI can be plugged into `docker/compose`.

---
## File: gettingstarted.md

---
description: Follow this hands-on tutorial to learn how to use Docker Compose from defining application
  dependencies to experimenting with commands.
keywords: docker compose example, docker compose tutorial, how to use docker compose,
  running docker compose, how to run docker compose, docker compose build image, docker
  compose command example, run docker compose file, how to create a docker compose
  file, run a docker compose file
title: Docker Compose Quickstart
linkTitle: Quickstart
weight: 30
aliases:
- /compose/support-and-feedback/samples-for-compose/
---

This tutorial aims to introduce fundamental concepts of Docker Compose by guiding you through the development of a basic Python web application. 

Using the Flask framework, the application features a hit counter in Redis, providing a practical example of how Docker Compose can be applied in web development scenarios. The concepts demonstrated here should be understandable even if you're not familiar with Python. 

## Prerequisites

Make sure you have:

- [Installed the latest version of Docker Compose](/manuals/compose/install/_index.md)
- A basic understanding of Docker concepts and how Docker works

## Step 1: Set up the project

1. Create a directory for the project:

   ```console
   $ mkdir compose-demo
   $ cd compose-demo
   ```

2. Create `app.py` in your project directory and add the following:

   ```python
   import os
   import redis
   from flask import Flask

   app = Flask(__name__)
   cache = redis.Redis(
       host=os.getenv("REDIS_HOST", "redis"),
       port=int(os.getenv("REDIS_PORT", "6379")),
   )

   @app.route("/")
   def hello():
       count = cache.incr("hits")
       return f"Hello from Docker! I have been seen {count} time(s).\n"
   ```

   The app reads its Redis connection details from environment variables, with sensible defaults so it works out of the box.

3. Create `requirements.txt` in your project directory and add the following:

   ```text
   flask
   redis
   ```

4. Create a `Dockerfile`:

   ```dockerfile
   # syntax=docker/dockerfile:1
   
   # Build an image with the Python 3.12 image
   FROM python:3.12-alpine
   
   # Set the working directory to `/code`
   WORKDIR /code
   
   # Set environment variables used by the `flask` command
   ENV FLASK_APP=app.py
   ENV FLASK_RUN_HOST=0.0.0.0
   
   # Install `gcc` and other dependencies
   RUN apk add --no-cache gcc musl-dev linux-headers
   
   # Copy `requirements.txt`
   COPY requirements.txt .
   
   # Install the Python dependencies
   RUN pip install -r requirements.txt
   
   # Copy the current directory `.` in the project to the workdir `.` in the image
   COPY . .
   
   EXPOSE 5000
   
   # Set the default command for the container to `flask run --debug`
   CMD ["flask", "run", "--debug"]
   ```

   > [!IMPORTANT]
   >
   > Make sure the file is named `Dockerfile` with no extension. Some editors add `.txt`
   > automatically, which causes the build to fail.

   For more information on how to write Dockerfiles, see the [Dockerfile reference](/reference/dockerfile/).

5. Create a `.env` file to hold configuration values:

   ```text
   APP_PORT=8000
   REDIS_HOST=redis
   REDIS_PORT=6379
   ```

   Compose automatically reads `.env` and makes these values available for interpolation
   in your `compose.yaml`. For this example the gains are modest, but in practice,
   keeping configuration out of the Compose file makes it easier to:
   - Change values across environments without editing YAML
   - Avoid committing secrets to version control
   - Reuse values across multiple services

6. Create a `.dockerignore` file to keep unnecessary files out of your build context:

   ```text
   .env
   *.pyc
   __pycache__
   redis-data
   ```

   Docker sends everything in your project directory to the daemon when it builds an image.
   Without `.dockerignore`, that includes your `.env` file (which may contain secrets) and
   any cached Python bytecode. Excluding them keeps builds fast and avoids accidentally
   baking sensitive values into an image layer.

## Step 2: Define and start your services

Compose simplifies the control of your entire application stack, making it easy to manage services, networks, and volumes in a single YAML configuration file. 

1. Create `compose.yaml` in your project directory and paste the following:

   ```yaml
   services:
     web:
       build: .
       ports:
         - "${APP_PORT}:5000"
       environment:
         - REDIS_HOST=${REDIS_HOST}
         - REDIS_PORT=${REDIS_PORT}

     redis:
       image: redis:alpine
   ```

   This Compose file defines two services: 

   - The `web` service uses an image that's built from the `Dockerfile` in the current directory. It maps port `8000` on the host to port `5000` on the container where Flask listens by default.

   - The `redis` service uses a public [Redis](https://registry.hub.docker.com/_/redis/) image pulled from the Docker Hub registry.

   For more information on the `compose.yaml` file, see [How Compose works](compose-application-model.md).

2. Start up your application: 

   ```console
   $ docker compose up
   ```

   With a single command, you create and start all the services from your configuration file. Compose builds your web image, pulls the Redis image, and starts both containers. 

3. Open `http://localhost:8000`. You should see:

   ```text
   Hello from Docker! I have been seen 1 time(s).
   ```

   Refresh the page — the counter increments on each visit.

   This minimal setup works, but it has two problems you'll fix in the next steps:

   - Startup race: `web` starts at the same time as `redis`. If Redis isn't ready yet,
   the Flask app fails to connect and crashes.
   - No persistence: If you run `docker compose down` followed by `docker compose up`, the
   counter resets to zero. `docker compose down` removes the containers, and with them
   any data written to the container's writable layer. `docker compose stop` preserves
   the containers so data survives, but you can't rely on that in production where
   containers are regularly replaced.

4. Stop the stack before moving on:

   ```console
   $ docker compose down
   ```

## Step 3: Fix the startup race with health checks

To fix the startup race, Compose needs to wait until `redis` is confirmed healthy before
starting `web`.

1. Update `compose.yaml`:

   ```yaml
   services:
     web:
       build: .
       ports:
         - "${APP_PORT}:5000"
       environment:
         - REDIS_HOST=${REDIS_HOST}
         - REDIS_PORT=${REDIS_PORT}
       depends_on:
         redis:
           condition: service_healthy

     redis:
       image: redis:alpine
       healthcheck:
         test: ["CMD", "redis-cli", "ping"]
         interval: 5s
         timeout: 3s
         retries: 5
         start_period: 10s
   ```

   The `healthcheck` block tells Compose how to test whether Redis is ready:

   - `test` is the command Compose runs inside the container to check its health.
     `redis-cli ping` connects to Redis and expects a `PONG` response — if it gets one,
     the container is healthy.
   - `start_period` gives Redis 10 seconds to initialize before health checks begin.
     Any failures during this window don't count toward the retry limit.
   - `interval` runs the check every 5 seconds after the start period has elapsed.
   - `timeout` gives each check 3 seconds to respond before treating it as a failure.
   - `retries` sets how many consecutive failures are allowed before Compose marks the
     container as unhealthy. With `interval: 5s` and `retries: 5`, Compose will wait up
     to 25 seconds before giving up.

2. Start the stack to confirm the ordering is fixed:

   ```console
   $ docker compose up
   ```

   You should see something similar to:

   ```text
   [+] Running 2/2
   ✔ Container compose-demo-redis-1  Healthy                       0.0s
   ```

3. Open `http://localhost:8000` to confirm the app is still working, then stop the stack before moving on:

   ```console
   $ docker compose down
   ```

## Step 4: Enable Compose Watch for live updates

Without Compose Watch, every code change requires you to stop the stack, rebuild the image, and restart the containers. Compose Watch eliminates that cycle by automatically syncing changes into your running container as you save files.

1. Update `compose.yaml` to add the `develop.watch` block to the `web` service:
   
   ```yaml
   services:
     web:
       build: .
       ports:
         - "${APP_PORT}:5000"
       environment:
         - REDIS_HOST=${REDIS_HOST}
         - REDIS_PORT=${REDIS_PORT}
       depends_on:
         redis:
           condition: service_healthy
       develop:
         watch:
           - action: sync+restart
             path: .
             target: /code
           - action: rebuild
             path: requirements.txt

     redis:
       image: redis:alpine
       healthcheck:
         test: ["CMD", "redis-cli", "ping"]
         interval: 5s
         timeout: 3s
         retries: 5
         start_period: 10s
   ```

   The `watch` block defines two rules:
   - The `sync+restart` action watches your project directory (`.`) on the host. When a file changes, Compose copies any changed files into `/code` inside the running container, then restarts the container. Because the container restarts with the updated files already in place, Flask starts up reading the new code directly — no manual rebuild or restart needed. 
   - The `rebuild` action on `requirements.txt` triggers a full image rebuild whenever you add a new dependency, since installing packages requires rebuilding the image, not just syncing files.
   
2. Start the stack with Watch enabled:

   ```console
   $ docker compose up --watch
   ```

3. Make a live change. Open `app.py` and update the greeting:

   ```python
   return f"Hello from Compose Watch! I have been seen {count} time(s).\n"
   ```

4. Save the file. Compose Watch detects the change and syncs it immediately:

   ```text
   Syncing service "web" after changes were detected
   ```

5. Refresh `http://localhost:8000`. The updated greeting appears without any restart
   and the counter should still be incrementing.

6. Stop the stack before moving on:

   ```console
   $ docker compose down
   ```

   For more information on how Compose Watch works, see [Use Compose Watch](/manuals/compose/how-tos/file-watch.md).

## Step 5: Persist data with named volumes

Each time you stop and restart the stack the visit counter resets to zero. Redis data
lives inside the container, so it disappears when the container is removed. A named
volume fixes this by storing the data on the host, outside the container lifecycle.

1. Update `compose.yaml`:

   ```yaml
   services:
     web:
       build: .
       ports:
         - "${APP_PORT}:5000"
       environment:
         - REDIS_HOST=${REDIS_HOST}
         - REDIS_PORT=${REDIS_PORT}
       depends_on:
         redis:
           condition: service_healthy
       develop:
         watch:
           - action: sync+restart
             path: .
             target: /code
           - action: rebuild
             path: requirements.txt

     redis:
       image: redis:alpine
       volumes:
         - redis-data:/data
       healthcheck:
         test: ["CMD", "redis-cli", "ping"]
         interval: 5s
         timeout: 3s
         retries: 5
         start_period: 10s

   volumes:
     redis-data:
   ```

   The `redis-data:/data` entry under `redis.volumes` mounts the named volume at `/data`, the path where Redis
   writes its data files. The top-level `volumes` key registers it with Docker so it
   persists between `compose down` and `compose up` cycles.

2. Start the stack with `docker compose up --watch` and refresh `http://localhost:8000` a few times to build up a count.

3. Tear down the stack with `docker compose down` and then bring it back up again with `docker compose up --watch`.

4. Open `http://localhost:8000` — the counter continues from where it left off.

5. Now reset the counter with `docker compose down -v`. 

   The `-v` flag removes named volumes along with the containers. Use this intentionally — it permanently deletes the stored data.

## Step 6: Structure your project with multiple Compose files

As applications grow, a single `compose.yaml` becomes harder to maintain. The `include`
top-level element lets you split services across multiple files while keeping them part of the
same application.

This is especially useful when different teams own different parts of the stack, or when
you want to reuse infrastructure definitions across projects.

1. Create a new file in your project directory called `infra.yaml` and move the Redis service and volume into it:

   ```yaml
   services:
     redis:
       image: redis:alpine
       volumes:
         - redis-data:/data
       healthcheck:
         test: ["CMD", "redis-cli", "ping"]
         interval: 5s
         timeout: 3s
         retries: 5
         start_period: 10s

   volumes:
     redis-data:
   ```

2. Update `compose.yaml` to include `infra.yaml`:

   ```yaml
   include:
      - path: ./infra.yaml
   services:
     web:
       build: .
       ports:
         - "${APP_PORT}:5000"
       environment:
         - REDIS_HOST=${REDIS_HOST}
         - REDIS_PORT=${REDIS_PORT}
       depends_on:
         redis:
           condition: service_healthy
       develop:
         watch:
           - action: sync+restart
             path: .
             target: /code
           - action: rebuild
             path: requirements.txt
   ```

3. Run the application to confirm everything still works:

   ```console
   $ docker compose up --watch
   ```

   Compose merges both files at startup. The `web` service can still reference `redis`
   by name because all included services share the same default network.

   This is a simplified example, but it demonstrates the basic principle of `include` and how it can make it easier to modularize complex applications into sub-Compose files. For more information on `include` and working with multiple Compose files, see [Working with multiple Compose files](/manuals/compose/how-tos/multiple-compose-files/_index.md).

4. Stop the stack before moving on:

   ```console
   $ docker compose down
   ```

## Step 7: Inspect and debug your running stack

With a fully configured stack, you can observe what's happening inside your containers
without stopping anything. This step covers the core commands for inspecting the resolved configuration, streaming logs, and running commands
inside a running container.

Before starting the stack, verify that Compose has resolved your `.env` variables and
merged all files correctly:

```console
$ docker compose config
```

`docker compose config` doesn't require the stack to be running — it works purely from
your files. A few things worth noting in the output:

- `${APP_PORT}`, `${REDIS_HOST}`, and `${REDIS_PORT}` have all been replaced with the
  values from your `.env` file.
- Short-form port notation (`"8000:5000"`) is expanded into its canonical fields
  (`target`, `published`, `protocol`).
- The default network and volume names are made explicit, prefixed with the project name
  `compose-demo`.
- The output is the fully resolved configuration, with any files
  brought in via `include` merged into a single view.

Use `docker compose config` any time you want to confirm what Compose will actually
apply, especially when debugging variable substitution or working with multiple Compose files.

Now start the stack in detached mode so the terminal stays free for the commands that
follow:

```console
$ docker compose up -d
```

### Stream logs from all services

```console
$ docker compose logs -f
```

The `-f` flag follows the log stream in real time, interleaving output from both
containers with color-coded service name prefixes. Refresh `http://localhost:8000` a
few times and watch the Flask request logs appear. To follow logs for a single service,
pass its name:

```console
$ docker compose logs -f web
```

Press `Ctrl+C` to stop following logs. The containers keep running.

### Run commands inside a running container

`docker compose exec` runs a command inside an already-running container without
starting a new one. This is the primary tool for live debugging.

#### Verify environment variables are set correctly

```console
$ docker compose exec web env | grep REDIS
```

```text
REDIS_HOST=redis
REDIS_PORT=6379
```

#### Test that the `web` container can reach Redis using the service name as the hostname

```console
$ docker compose exec web python -c "import redis; r = redis.Redis(host='redis'); print(r.ping())"
```

```text
True
```

This uses the same `redis` library your app uses, so a `True` response confirms that
service discovery, networking, and the Redis connection are all working end to end.

#### Inspect the live value of the hit counter in Redis

```console
$ docker compose exec redis redis-cli GET hits
```

## Where to go next

- [Explore the full list of Compose commands](/reference/cli/docker/compose/)
- [Explore the Compose file reference](/reference/compose-file/_index.md)
- [Check out the Learning Docker Compose video on LinkedIn Learning](https://www.linkedin.com/learning/learning-docker-compose/)
- [Learn how to set environment variables in Compose](/compose/how-tos/environment-variables/set-environment-variables/)
- [Learn how to package and distribute your Compose app](/compose/how-tos/oci-artifact/)




---
## File: dependent-images.md

---
description: Build images for services with shared definition
keywords: compose, build
title: Build dependent images
weight: 50
---

{{< summary-bar feature_name="Compose dependent images" >}}

To reduce push/pull time and image weight, a common practice for Compose applications is to have services
share base layers as much as possible. You typically select the same operating system base image for
all services. But you can also get one step further by sharing image layers when your images share the same
system packages. The challenge to address is then to avoid repeating the exact same Dockerfile instruction 
in all services.

For illustration, this page assumes you want all your services to be built with an `alpine` base
image and install the system package `openssl`.

## Multi-stage Dockerfile

The recommended approach is to group the shared declaration in a single Dockerfile, and use multi-stage features
so that service images are built from this shared declaration.

Dockerfile:

```dockerfile
FROM alpine as base
RUN /bin/sh -c apk add --update --no-cache openssl

FROM base as service_a
# build service a
...

FROM base as service_b
# build service b
...
```

Compose file:

```yaml
services:
  a:
     build:
       target: service_a
  b:
     build:
       target: service_b
```

## Use another service's image as the base image

A popular pattern is to reuse a service image as a base image in another service.
As Compose does not parse the Dockerfile, it can't automatically detect this dependency 
between services to correctly order the build execution.

a.Dockerfile:

```dockerfile
FROM alpine
RUN /bin/sh -c apk add --update --no-cache openssl
```

b.Dockerfile:

```dockerfile
FROM service_a
# build service b
```

Compose file:

```yaml
services:
  a:
     image: service_a 
     build:
       dockerfile: a.Dockerfile
  b:
     image: service_b
     build:
       dockerfile: b.Dockerfile
```

Legacy Docker Compose v1 used to build images sequentially, which made this pattern usable
out of the box. Compose v2 uses BuildKit to optimise builds and build images in parallel 
and requires an explicit declaration.

The recommended approach is to declare the dependent base image as an additional build context:

Compose file:

```yaml
services:
  a:
     image: service_a
     build: 
       dockerfile: a.Dockerfile
  b:
     image: service_b
     build:
       dockerfile: b.Dockerfile
       additional_contexts:
         # `FROM service_a` will be resolved as a dependency on service "a" which has to be built first
         service_a: "service:a"
```

With the `additional_contexts` attribute, you can refer to an image built by another service without needing to explicitly name it:

b.Dockerfile:

```dockerfile

FROM base_image  
# `base_image` doesn't resolve to an actual image. This is used to point to a named additional context

# build service b
```

Compose file:

```yaml
services:
  a:
     build: 
       dockerfile: a.Dockerfile
       # built image will be tagged <project_name>_a
  b:
     build:
       dockerfile: b.Dockerfile
       additional_contexts:
         # `FROM base_image` will be resolved as a dependency on service "a" which has to be built first
         base_image: "service:a"
```

## Build with Bake

Using [Bake](/manuals/build/bake/_index.md) let you pass the complete build definition for all services
and to orchestrate build execution in the most efficient way. 

To enable this feature, run Compose with the `COMPOSE_BAKE=true` variable set in your environment.

```console
$ COMPOSE_BAKE=true docker compose build
[+] Building 0.0s (0/1)                                                         
 => [internal] load local bake definitions                                 0.0s
...
[+] Building 2/2 manifest list sha256:4bd2e88a262a02ddef525c381a5bdb08c83  0.0s
 ✔ service_b  Built                                                        0.7s 
 ✔ service_a  Built    
```

Bake can also be selected as the default builder by editing your `$HOME/.docker/config.json` config file:
```json
{
  ...
  "plugins": {
    "compose": {
      "build": "bake"
    }
  }
  ...
}
```

## Additional resources

- [Docker Compose build reference](/reference/cli/docker/compose/build/)
- [Learn about multi-stage Dockerfiles](/manuals/build/building/multi-stage.md)


---
## File: best-practices.md

---
title: Best practices for working with environment variables in Docker Compose
linkTitle: Best practices
description: Explainer on the best ways to set, use, and manage environment variables in
  Compose
keywords: compose, orchestration, environment, env file, environment variables
tags: [Best practices]
weight: 50
---

#### Handle sensitive information securely

Be cautious about including sensitive data in environment variables. Consider using [Secrets](../use-secrets.md) for managing sensitive information.

#### Understand environment variable precedence

Be aware of how Docker Compose handles the [precedence of environment variables](envvars-precedence.md) from different sources (`.env` files, shell variables, Dockerfiles).

#### Use specific environment files

Consider how your application adapts to different environments. For example development, testing, production, and use different `.env` files as needed.

#### Know interpolation
   
Understand how [interpolation](variable-interpolation.md) works within compose files for dynamic configurations.

#### Command line overrides
    
Be aware that you can [override environment variables](set-environment-variables.md#cli) from the command line when starting containers. This is useful for testing or when you have temporary changes.



---
## File: envvars.md

---
description: Compose pre-defined environment variables
keywords: fig, composition, compose, docker, orchestration, cli, reference, compose environment configuration, docker env variables
title: Configure pre-defined environment variables in Docker Compose
linkTitle: Pre-defined environment variables
weight: 30
aliases:
- /compose/reference/envvars/
- /compose/environment-variables/envvars/
---

Docker Compose includes several pre-defined environment variables. It also inherits common Docker CLI environment variables, such as `DOCKER_HOST` and `DOCKER_CONTEXT`. See [Docker CLI environment variable reference](/reference/cli/docker/#environment-variables) for details.

This page explains how to set or change the following pre-defined environment variables:

- `COMPOSE_PROJECT_NAME`
- `COMPOSE_FILE`
- `COMPOSE_PROFILES`
- `COMPOSE_CONVERT_WINDOWS_PATHS`
- `COMPOSE_PATH_SEPARATOR`
- `COMPOSE_IGNORE_ORPHANS`
- `COMPOSE_REMOVE_ORPHANS`
- `COMPOSE_PARALLEL_LIMIT`
- `COMPOSE_ANSI`
- `COMPOSE_STATUS_STDOUT`
- `COMPOSE_ENV_FILES`
- `COMPOSE_DISABLE_ENV_FILE`
- `COMPOSE_MENU`
- `COMPOSE_EXPERIMENTAL`
- `COMPOSE_PROGRESS`

## Methods to override 

| Method      | Description                                  |
| ----------- | -------------------------------------------- |
| [`.env` file](/manuals/compose/how-tos/environment-variables/variable-interpolation.md) | Located in the working directory.            |
| [Shell](variable-interpolation.md#substitute-from-the-shell)       | Defined in the host operating system shell.  |
| CLI         | Passed with `--env` or `-e` flag at runtime. |

When changing or setting any environment variables, be aware of [Environment variable precedence](envvars-precedence.md).

## Configuration details

### Project and file configuration

#### COMPOSE\_PROJECT\_NAME

Sets the project name. This value is prepended along with the service name to
the container's name on startup.

For example, if your project name is `myapp` and it includes two services `db` and `web`, 
then Compose starts containers named `myapp-db-1` and `myapp-web-1` respectively.

Compose can set the project name in different ways. The level of precedence (from highest to lowest) for each method is as follows:

1. The `-p` command line flag 
2. `COMPOSE_PROJECT_NAME`
3. The top-level `name:` variable from the config file (or the last `name:` from
  a series of config files specified using `-f`)
4. The `basename` of the project directory containing the config file (or
  containing the first config file specified using `-f`)
5. The `basename` of the current directory if no config file is specified

Project names must contain only lowercase letters, decimal digits, dashes, and
underscores, and must begin with a lowercase letter or decimal digit. If the
`basename` of the project directory or current directory violates this
constraint, you must use one of the other mechanisms.

See also [using `-p` to specify a project name](/reference/cli/docker/compose/#use--p-to-specify-a-project-name).

#### COMPOSE\_FILE

Specifies the path to a Compose file. Specifying multiple Compose files is supported.

- Default behavior: If not provided, Compose looks for a file named `compose.yaml` in the current directory and, if not found, then Compose searches each parent directory recursively until a file by that name is found.
- When specifying multiple Compose files, the path separators are, by default, on:
   - Mac and Linux: `:` (colon)
   - Windows: `;` (semicolon)
   For example:

      ```console
      COMPOSE_FILE=compose.yaml:compose.prod.yaml
      ```  
   The path separator can also be customized using [`COMPOSE_PATH_SEPARATOR`](#compose_path_separator).  

See also [using `-f` to specify name and path of one or more Compose files](/reference/cli/docker/compose/#use--f-to-specify-the-name-and-path-of-one-or-more-compose-files).

#### COMPOSE\_PROFILES

Specifies one or more profiles to be enabled when `docker compose up` is run.

Services with matching profiles are started as well as any services for which no profile has been defined.

For example, calling `docker compose up` with `COMPOSE_PROFILES=frontend` selects services with the 
`frontend` profile as well as any services without a profile specified.

If specifying multiple profiles, use a comma as a separator.

The following example enables all services matching both the `frontend` and `debug` profiles and services without a profile. 

```console
COMPOSE_PROFILES=frontend,debug
```

See also [Using profiles with Compose](../profiles.md) and the [`--profile` command-line option](/reference/cli/docker/compose/#use-profiles-to-enable-optional-services).

#### COMPOSE\_PATH\_SEPARATOR

Specifies a different path separator for items listed in `COMPOSE_FILE`.

- Defaults to:
    - On macOS and Linux to `:`
    - On Windows to`;`

#### COMPOSE\_ENV\_FILES

Specifies which environment files Compose should use if `--env-file` isn't used.

When using multiple environment files, use a comma as a separator. For example: 

```console
COMPOSE_ENV_FILES=.env.envfile1,.env.envfile2
```

If `COMPOSE_ENV_FILES` is not set, and you don't provide `--env-file` in the CLI, Docker Compose uses the default behavior, which is to look for an `.env` file in the project directory.

#### COMPOSE\_DISABLE\_ENV\_FILE

Lets you disable the use of the default `.env` file. 

- Supported values: 
    - `true` or `1`, Compose ignores the `.env` file
    - `false` or `0`, Compose looks for an `.env` file in the project directory
- Defaults to: `0`

### Environment handling and container lifecycle

#### COMPOSE\_CONVERT\_WINDOWS\_PATHS

When enabled, Compose performs path conversion from Windows-style to Unix-style in volume definitions.

- Supported values: 
    - `true` or `1`, to enable
    - `false` or `0`, to disable
- Defaults to: `0`

#### COMPOSE\_IGNORE\_ORPHANS

When enabled, Compose doesn't try to detect orphaned containers for the project.

- Supported values: 
   - `true` or `1`, to enable
   - `false` or `0`, to disable
- Defaults to: `0`

#### COMPOSE\_REMOVE\_ORPHANS

When enabled, Compose automatically removes orphaned containers when updating a service or stack. Orphaned containers are those that were created by a previous configuration but are no longer defined in the current `compose.yaml` file.

- Supported values:
   - `true` or `1`, to enable automatic removal of orphaned containers
   - `false` or `0`, to disable automatic removal. Compose displays a warning about orphaned containers instead.
- Defaults to: `0`

#### COMPOSE\_PARALLEL\_LIMIT

Specifies the maximum level of parallelism for concurrent engine calls.

### Output 

#### COMPOSE\_ANSI

Specifies when to print ANSI control characters. 

- Supported values:
   - `auto`, Compose detects if TTY mode can be used. Otherwise, use plain text mode
   - `never`, use plain text mode
   - `always` or `0`, use TTY mode
- Defaults to: `auto`

#### COMPOSE\_STATUS\_STDOUT

When enabled, Compose writes its internal status and progress messages to `stdout` instead of `stderr`. 
The default value is false to clearly separate the output streams between Compose messages and your container's logs.

- Supported values:
   - `true` or `1`, to enable
   - `false` or `0`, to disable
- Defaults to: `0`

#### COMPOSE\_PROGRESS

{{< summary-bar feature_name="Compose progress" >}}

Defines the type of progress output, if `--progress` isn't used. 

Supported values are `auto`, `tty`, `plain`, `json`, and `quiet`.
Default is `auto`. 

### User experience

#### COMPOSE\_MENU

{{< summary-bar feature_name="Compose menu" >}}

When enabled, Compose displays a navigation menu where you can choose to open the Compose stack in Docker Desktop, switch on [`watch` mode](../file-watch.md), or use [Docker Debug](/reference/cli/docker/debug/).

- Supported values:
   - `true` or `1`, to enable
   - `false` or `0`, to disable
- Defaults to: `1` if you obtained Docker Compose through Docker Desktop, otherwise the default is `0`

#### COMPOSE\_EXPERIMENTAL

{{< summary-bar feature_name="Compose experimental" >}}

This is an opt-out variable. When turned off it deactivates the experimental features.

- Supported values:
   - `true` or `1`, to enable
   - `false` or `0`, to disable
- Defaults to: `1`

## Unsupported in Compose V2

The following environment variables have no effect in Compose V2.

- `COMPOSE_API_VERSION`
    By default the API version is negotiated with the server. Use `DOCKER_API_VERSION`.  
    See the [Docker CLI environment variable reference](/reference/cli/docker/#environment-variables) page.
- `COMPOSE_HTTP_TIMEOUT`
- `COMPOSE_TLS_VERSION`
- `COMPOSE_FORCE_WINDOWS_HOST`
- `COMPOSE_INTERACTIVE_NO_CLI`
- `COMPOSE_DOCKER_CLI_BUILD`
    Use `DOCKER_BUILDKIT` to select between BuildKit and the classic builder. If `DOCKER_BUILDKIT=0` then `docker compose build` uses the classic builder to build images.



---
## File: envvars-precedence.md

---
title: Environment variables precedence in Docker Compose
linkTitle: Environment variables precedence
description: Scenario overview illustrating how environment variables are resolved
  in Compose
keywords: compose, environment, env file
weight: 20
aliases:
- /compose/environment-variables/envvars-precedence/
---

When the same environment variable is set in multiple sources, Docker Compose follows a precedence rule to determine the value for that variable in your container's environment.

This page explains how Docker Compose determines the final value of an environment variable when it's defined in multiple locations.

The order of precedence (highest to lowest) is as follows:
1. Set using [`docker compose run -e` in the CLI](set-environment-variables.md#set-environment-variables-with-docker-compose-run---env).
2. Set with either the `environment` or `env_file` attribute but with the value interpolated from your [shell](variable-interpolation.md#substitute-from-the-shell) or an environment file. (either your default [`.env` file](variable-interpolation.md#env-file), or with the [`--env-file` argument](variable-interpolation.md#substitute-with---env-file) in the CLI).
3. Set using just the [`environment` attribute](set-environment-variables.md#use-the-environment-attribute) in the Compose file.
4. Use of the [`env_file` attribute](set-environment-variables.md#use-the-env_file-attribute) in the Compose file.
5. Set in a container image in the [ENV directive](/reference/dockerfile.md#env).
   Having any `ARG` or `ENV` setting in a `Dockerfile` evaluates only if there is no Docker Compose entry for `environment`, `env_file` or `run --env`.

> [!NOTE] 
> 
> When `--env-file` is not set, Compose may load up to two `.env` files.
> It first loads one from the project directory (determined by `--project-directory`
> if set, otherwise the directory of the first `-f`/`--file` Compose file, otherwise
> `PWD`). If that file sets `COMPOSE_FILE` to a path in a different directory, Compose
> loads a second `.env` file from that directory with lower precedence. For more
> information, see [local `.env` file versus project directory `.env` file](variable-interpolation.md#local-env-file-versus-project-directory-env-file).

## Simple example

In the following example, a different value for the same environment variable in an `.env` file and with the `environment` attribute in the Compose file:

```console
$ cat ./webapp.env
NODE_ENV=test

$ cat compose.yaml
services:
  webapp:
    image: 'webapp'
    env_file:
     - ./webapp.env
    environment:
     - NODE_ENV=production
```

The environment variable defined with the `environment` attribute takes precedence.

```console
$ docker compose run webapp env | grep NODE_ENV
NODE_ENV=production
```

## Advanced example 

The following table uses `VALUE`, an environment variable defining the version for an image, as an example.

### How the table works

Each column represents a context from where you can set a value, or substitute in a value for `VALUE`.

The columns `Host OS environment` and `.env` file is listed only for illustration purposes. In reality, they don't result in a variable in the container by itself, but in conjunction with either the `environment` or `env_file` attribute.

Each row represents a combination of contexts where `VALUE` is set, substituted, or both. The **Result** column indicates the final value for `VALUE` in each scenario.

|  # |  `docker compose run`  |  `environment` attribute  |  `env_file` attribute  |  Image `ENV` |  `Host OS` environment  |  `.env` file      |   Result  |
|:--:|:----------------:|:-------------------------------:|:----------------------:|:------------:|:-----------------------:|:-----------------:|:----------:|
|  1 |   -              |   -                             |   -                    |   -          |  `VALUE=1.4`            |  `VALUE=1.3`      | -               |
|  2 |   -              |   -                             |  `VALUE=1.6`           |  `VALUE=1.5` |  `VALUE=1.4`            |   -               |**`VALUE=1.6`**  |
|  3 |   -              |  `VALUE=1.7`                    |   -                    |  `VALUE=1.5` |  `VALUE=1.4`            |   -               |**`VALUE=1.7`**  |
|  4 |   -              |   -                             |   -                    |  `VALUE=1.5` |  `VALUE=1.4`            |  `VALUE=1.3`      |**`VALUE=1.5`**  |
|  5 |`--env VALUE=1.8` |   -                             |   -                    |  `VALUE=1.5` |  `VALUE=1.4`            |  `VALUE=1.3`      |**`VALUE=1.8`**  |
|  6 |`--env VALUE`     |   -                             |   -                    |  `VALUE=1.5` |  `VALUE=1.4`            |  `VALUE=1.3`      |**`VALUE=1.4`**  |
|  7 |`--env VALUE`     |   -                             |   -                    |  `VALUE=1.5` |   -                     |  `VALUE=1.3`      |**`VALUE=1.3`**  |
|  8 |   -              |   -                             |   `VALUE`              |  `VALUE=1.5` |  `VALUE=1.4`            |  `VALUE=1.3`      |**`VALUE=1.4`**  |
|  9 |   -              |   -                             |   `VALUE`              |  `VALUE=1.5` |   -                     |  `VALUE=1.3`      |**`VALUE=1.3`**  |
| 10 |   -              |  `VALUE`                        |   -                    |  `VALUE=1.5` |  `VALUE=1.4`            |  `VALUE=1.3`      |**`VALUE=1.4`**  |
| 11 |   -              |  `VALUE`                        |   -                    |  `VALUE=1.5` |  -                      |  `VALUE=1.3`      |**`VALUE=1.3`**  |
| 12 |`--env VALUE`     |  `VALUE=1.7`                    |   -                    |  `VALUE=1.5` |  `VALUE=1.4`            |  `VALUE=1.3`      |**`VALUE=1.4`**  |
| 13 |`--env VALUE=1.8` |  `VALUE=1.7`                    |   -                    |  `VALUE=1.5` |  `VALUE=1.4`            |  `VALUE=1.3`      |**`VALUE=1.8`**  |
| 14 |`--env VALUE=1.8` |   -                             |  `VALUE=1.6`           |  `VALUE=1.5` |  `VALUE=1.4`            |  `VALUE=1.3`      |**`VALUE=1.8`**  |
| 15 |`--env VALUE=1.8` |  `VALUE=1.7`                    |  `VALUE=1.6`           |  `VALUE=1.5` |  `VALUE=1.4`            |  `VALUE=1.3`      |**`VALUE=1.8`**  |

### Understanding precedence results

Result 1: The local environment takes precedence, but the Compose file is not set to replicate this inside the container, so no such variable is set.

Result 2: The `env_file` attribute in the Compose file defines an explicit value for `VALUE` so the container environment is set accordingly.

Result 3: The `environment` attribute in the Compose file defines an explicit value for `VALUE`, so the container environment is set accordingly.

Result 4: The image's `ENV` directive declares the variable `VALUE`, and since the Compose file is not set to override this value, this variable is defined by image

Result 5: The `docker compose run` command has the `--env` flag set with an explicit value, and overrides the value set by the image. 

Result 6: The `docker compose run` command has the `--env` flag set to replicate the value from the environment. Host OS value takes precedence and is replicated into the container's environment.

Result 7: The `docker compose run` command has the `--env` flag set to replicate the value from the environment. Value from `.env` file is selected to define the container's environment.

Result 8: The `env_file` attribute in the Compose file is set to replicate `VALUE` from the local environment. Host OS value takes precedence and is replicated into the container's environment.

Result 9: The `env_file` attribute in the Compose file is set to replicate `VALUE` from the local environment. Value from `.env` file is selected to define the container's environment.

Result 10: The `environment` attribute in the Compose file is set to replicate `VALUE` from the local environment. Host OS value takes precedence and is replicated into the container's environment.

Result 11: The `environment` attribute in the Compose file is set to replicate `VALUE` from the local environment. Value from `.env` file is selected to define the container's environment.

Result 12: The `--env` flag has higher precedence than the `environment` and `env_file` attributes and is to set to replicate `VALUE` from the local environment. Host OS value takes precedence and is replicated into the container's environment.

Results 13 to 15: The `--env` flag has higher precedence than the `environment` and `env_file` attributes and so sets the value. 

## Next steps

- [Set environment variables in Compose](set-environment-variables.md)
- [Use variable interpolation in Compose files](variable-interpolation.md)


---
## File: _index.md

---
title: Environment variables in Compose
linkTitle: Use environment variables
weight: 40
description: Explains how to set, use, and manage environment variables in Docker Compose.
keywords: compose, orchestration, environment, env file
aliases:
- /compose/environment-variables/
---

Environment variables and interpolation in Docker Compose help you create reusable, flexible configurations. This makes Dockerized applications easier to manage and deploy across environments.

> [!TIP]
>
> Before using environment variables, read through all of the information first to get a full picture of environment variables in Docker Compose.

This section covers:

- [How to set environment variables within your container's environment](set-environment-variables.md).
- [How environment variable precedence works within your container's environment](envvars-precedence.md).
- [Pre-defined environment variables](envvars.md).

It also covers: 
- How [interpolation](variable-interpolation.md) can be used to set variables within your Compose file and how it relates to a container's environment.
- Some [best practices](best-practices.md).


---
## File: set-environment-variables.md

---
title: Set environment variables within your container's environment
linkTitle: Set environment variables
weight: 10
description: How to set, use, and manage environment variables with Compose
keywords: compose, orchestration, environment, environment variables, container environment variables
aliases:
- /compose/environment-variables/set-environment-variables/
---

A container's environment is not set until there's an explicit entry in the service configuration to make this happen. With Compose, there are two ways you can set environment variables in your containers with your Compose file. 

>[!TIP]
>
> Don't use environment variables to pass sensitive information, such as passwords, in to your containers. Use [secrets](../use-secrets.md) instead.


## Use the `environment` attribute

You can set environment variables directly in your container's environment with the
[`environment` attribute](/reference/compose-file/services.md#environment) in your `compose.yaml`.

It supports both list and mapping syntax:

```yaml
services:
  webapp:
    environment:
      DEBUG: "true"
```
is equivalent to 
```yaml
services:
  webapp:
    environment:
      - DEBUG=true
```

See [`environment` attribute](/reference/compose-file/services.md#environment) for more examples on how to use it. 

### Additional information 

- You can choose not to set a value and pass the environment variables from your shell straight through to your containers. It works in the same way as `docker run -e VARIABLE ...`:
  ```yaml
  web:
    environment:
      - DEBUG
  ```
The value of the `DEBUG` variable in the container is taken from the value for the same variable in the shell in which Compose is run. Note that in this case no warning is issued if the `DEBUG` variable in the shell environment is not set. 

- You can also take advantage of [interpolation](variable-interpolation.md#interpolation-syntax). In the following example, the result is similar to the one above but Compose gives you a warning if the `DEBUG` variable is not set in the shell environment or in an `.env` file in the project directory.

  ```yaml
  web:
    environment:
      - DEBUG=${DEBUG}
  ```

## Use the `env_file` attribute

A container's environment can also be set using [`.env` files](variable-interpolation.md#env-file) along with the [`env_file` attribute](/reference/compose-file/services.md#env_file).

```yaml
services:
  webapp:
    env_file: "webapp.env"
```

Using an `.env` file lets you use the same file for use by a plain `docker run --env-file ...` command, or to share the same `.env` file within multiple services without the need to duplicate a long `environment` YAML block.

It can also help you keep your environment variables separate from your main configuration file, providing a more organized and secure way to manage sensitive information, as you do not need to place your `.env` file in the root of your project's directory.

The [`env_file` attribute](/reference/compose-file/services.md#env_file) also lets you use multiple `.env` files in your Compose application.  

The paths to your `.env` file, specified in the `env_file` attribute, are relative to the location of your `compose.yaml` file.

> [!IMPORTANT]
>
> Interpolation in `.env` files is a Docker Compose CLI feature.
>
> It is not supported when running `docker run --env-file ...`.

### Additional information 

- If multiple files are specified, they are evaluated in order and can override values set in previous files.
- As of Docker Compose version 2.24.0, you can set your `.env` file, defined by the `env_file` attribute, to be optional by using the `required` field. When `required` is set to `false` and the `.env` file is missing, Compose silently ignores the entry.
  ```yaml
  env_file:
    - path: ./default.env
      required: true # default
    - path: ./override.env
      required: false
  ``` 
- As of Docker Compose version 2.30.0, you can use an alternative file format for the `env_file` with the `format` attribute. For more information, see [`format`](/reference/compose-file/services.md#format).
- Values in your `.env` file can be overridden from the command line by using [`docker compose run -e`](#set-environment-variables-with-docker-compose-run---env). 

## Set environment variables with `docker compose run --env`

Similar to `docker run --env`, you can set environment variables temporarily with `docker compose run --env` or its short form `docker compose run -e`:

```console
$ docker compose run -e DEBUG=1 web python console.py
```

### Additional information 

- You can also pass a variable from the shell or your environment files by not giving it a value:

  ```console
  $ docker compose run -e DEBUG web python console.py
  ```

The value of the `DEBUG` variable in the container is taken from the value for the same variable in the shell in which Compose is run or from the environment files.

## Further resources

- [Understand environment variable precedence](envvars-precedence.md).
- [Set or change predefined environment variables](envvars.md)
- [Explore best practices](best-practices.md)
- [Understand interpolation](variable-interpolation.md)


---
## File: variable-interpolation.md

---
title: Set, use, and manage variables in a Compose file with interpolation
linkTitle: Interpolation
description: How to set, use, and manage variables in your Compose file with interpolation
keywords: compose, orchestration, environment, variables, interpolation
weight: 40
aliases:
- /compose/env-file/
- /compose/environment-variables/env-file/
- /compose/environment-variables/variable-interpolation/
---

A Compose file can use variables to offer more flexibility. If you want to quickly switch 
between image tags to test multiple versions, or want to adjust a volume source to your local
environment, you don't need to edit the Compose file each time, you can just set variables that insert values into your Compose file at runtime.

Interpolation can also be used to insert values into your Compose file at runtime, which is then used to pass variables into your container's environment

Below is a simple example: 

```console
$ cat .env
TAG=v1.5
$ cat compose.yaml
services:
  web:
    image: "webapp:${TAG}"
```

When you run `docker compose up`, the `web` service defined in the Compose file [interpolates](variable-interpolation.md) in the image `webapp:v1.5` which was set in the `.env` file. You can verify this with the
[config command](/reference/cli/docker/compose/config/), which prints your resolved application config to the terminal:

```console
$ docker compose config
services:
  web:
    image: 'webapp:v1.5'
```

## Interpolation syntax

Interpolation is applied for unquoted and double-quoted values.
Both braced (`${VAR}`) and unbraced (`$VAR`) expressions are supported.

For braced expressions, the following formats are supported:
- Direct substitution
  - `${VAR}` -> value of `VAR`
- Default value
  - `${VAR:-default}` -> value of `VAR` if set and non-empty, otherwise `default`
  - `${VAR-default}` -> value of `VAR` if set, otherwise `default`
- Required value
  - `${VAR:?error}` -> value of `VAR` if set and non-empty, otherwise exit with error
  - `${VAR?error}` -> value of `VAR` if set, otherwise exit with error
- Alternative value
  - `${VAR:+replacement}` -> `replacement` if `VAR` is set and non-empty, otherwise empty
  - `${VAR+replacement}` -> `replacement` if `VAR` is set, otherwise empty

For more information, see [Interpolation](/reference/compose-file/interpolation.md) in the Compose Specification. 

## Ways to set variables with interpolation

Docker Compose can interpolate variables into your Compose file from multiple sources. 

Note that when the same variable is declared by multiple sources, precedence applies:

1. Variables from your shell environment
2. Variables from a file set by `--env-file`
3. If `--env-file` is not set, variables from an `.env` file in the project directory,
   where the project directory is:
   - `--project-directory` if set
   - otherwise, the directory of the first Compose file specified with `-f`/`--file`
   - otherwise, your shell's current directory (`PWD`)

You can check variables and values used by Compose to interpolate the Compose model by running `docker compose config --environment`.

### `.env` file

An `.env` file in Docker Compose is a text file used to define variables that should be made available for interpolation when running `docker compose up`. This file typically contains key-value pairs of variables, and it lets you  centralize and manage configuration in one place. The `.env` file is useful if you have multiple variables you need to store.

The `.env` file is the default method for setting variables. The `.env` file should be placed at the root of the project directory next to your `compose.yaml` file. For more information on formatting an environment file, see [Syntax for environment files](#env-file-syntax).

Basic example: 

```console
$ cat .env
## define COMPOSE_DEBUG based on DEV_MODE, defaults to false
COMPOSE_DEBUG=${DEV_MODE:-false}

$ cat compose.yaml 
  services:
    webapp:
      image: my-webapp-image
      environment:
        - DEBUG=${COMPOSE_DEBUG}

$ DEV_MODE=true docker compose config
services:
  webapp:
    environment:
      DEBUG: "true"
```

#### Additional information 

- If you define a variable in your `.env` file, you can reference it directly in your `compose.yaml` with the [`environment` attribute](/reference/compose-file/services.md#environment). For example, if your `.env` file contains the environment variable `DEBUG=1` and your `compose.yaml` file looks like this:
   ```yaml
    services:
      webapp:
        image: my-webapp-image
        environment:
          - DEBUG=${DEBUG}
   ```
   Docker Compose replaces `${DEBUG}` with the value from the `.env` file

   > [!IMPORTANT]
   >
   > Be aware of [Environment variables precedence](envvars-precedence.md) when using variables in an `.env` file that  as environment variables in your container's environment.

- You can place your `.env` file in a location other than the root of your project's directory, and then use the [`--env-file` option in the CLI](#substitute-with---env-file) so Compose can navigate to it.

- Your `.env` file can be overridden by another `.env` if it is [substituted with `--env-file`](#substitute-with---env-file).

> [!IMPORTANT]
>
> Substitution from `.env` files is a Docker Compose CLI feature.
>
> It is not supported by Swarm when running `docker stack deploy`.

#### `.env` file syntax

The following syntax rules apply to environment files:

- Lines beginning with `#` are processed as comments and ignored.
- Blank lines are ignored.
- Unquoted and double-quoted (`"`) values have interpolation applied.
- Each line represents a key-value pair. Values can optionally be quoted.
- Delimiter separating key and value can be either `=` or `:`.
- Spaces before and after value are ignored.
  - `VAR=VAL` -> `VAL`
  - `VAR="VAL"` -> `VAL`
  - `VAR='VAL'` -> `VAL`
  - `VAR: VAL` -> `VAL`
  - `VAR = VAL  ` -> `VAL` <!-- markdownlint-disable-line no-space-in-code -->
- Inline comments for unquoted values must be preceded with a space.
  - `VAR=VAL # comment` -> `VAL`
  - `VAR=VAL# not a comment` -> `VAL# not a comment`
- Inline comments for quoted values must follow the closing quote.
  - `VAR="VAL # not a comment"` -> `VAL # not a comment`
  - `VAR="VAL" # comment` -> `VAL`
- Single-quoted (`'`) values are used literally.
  - `VAR='$OTHER'` -> `$OTHER`
  - `VAR='${OTHER}'` -> `${OTHER}`
- Quotes can be escaped with `\`.
  - `VAR='Let\'s go!'` -> `Let's go!`
  - `VAR="{\"hello\": \"json\"}"` -> `{"hello": "json"}`
- Common shell escape sequences including `\n`, `\r`, `\t`, and `\\` are supported in double-quoted values.
  - `VAR="some\tvalue"` -> `some  value`
  - `VAR='some\tvalue'` -> `some\tvalue`
  - `VAR=some\tvalue` -> `some\tvalue`
- Single-quoted values can span multiple lines. Example:

   ```yaml
   KEY='SOME
   VALUE'
   ```

   If you then run `docker compose config`, you'll see:
  
   ```yaml
   environment:
     KEY: |-
       SOME
       VALUE
   ```

### Substitute with `--env-file`

You can set default values for multiple environment variables, in an `.env` file and then pass the file as an argument in the CLI.

The advantage of this method is that you can store the file anywhere and name it appropriately, for example, 
This file path is relative to the current working directory where the Docker Compose command is executed. Passing the file path is done using the `--env-file` option:

```console
$ docker compose --env-file ./config/.env.dev up
```

#### Additional information 

- This method is useful if you want to temporarily override an `.env` file that is already referenced in your `compose.yaml` file. For example you may have different `.env` files for production ( `.env.prod`) and testing (`.env.test`).
  In the following example, there are two environment files, `.env` and `.env.dev`. Both have different values set for `TAG`. 
  ```console
  $ cat .env
  TAG=v1.5
  $ cat ./config/.env.dev
  TAG=v1.6
  $ cat compose.yaml
  services:
    web:
      image: "webapp:${TAG}"
  ```
  If the `--env-file` is not used in the command line, the `.env` file is loaded by default:
  ```console
  $ docker compose config
  services:
    web:
      image: 'webapp:v1.5'
  ```
  Passing the `--env-file` argument overrides the default file path:
  ```console
  $ docker compose --env-file ./config/.env.dev config
  services:
    web:
      image: 'webapp:v1.6'
  ```
  When an invalid file path is being passed as an `--env-file` argument, Compose returns an error:
  ```console
  $ docker compose --env-file ./doesnotexist/.env.dev  config
  ERROR: Couldn't find env file: /home/user/./doesnotexist/.env.dev
  ```
- You can use multiple `--env-file` options to specify multiple environment files, and Docker Compose reads them in order. Later files can override variables from earlier files.
  ```console
  $ docker compose --env-file .env --env-file .env.override up
  ```
- You can override specific environment variables from the command line when starting containers. 
  ```console
  $ docker compose --env-file .env.dev up -e DATABASE_URL=mysql://new_user:new_password@new_db:3306/new_database
  ```

### local `.env` file versus &lt;project directory&gt; `.env` file

An `.env` file can also be used to declare [pre-defined environment variables](envvars.md) used to control Compose behavior and files to be loaded. 

When executed without an explicit `--env-file` flag, Compose searches for an `.env` file
in the project directory and loads values both for self-configuration and interpolation.
The project directory is determined by `--project-directory` if set, otherwise by the
directory of the first Compose file specified with `-f`/`--file`, otherwise `PWD`.
If the values in this file define the `COMPOSE_FILE` pre-defined variable, which results
in a project directory being set to another folder, Compose loads a second `.env` file,
if present. This second `.env` file has a lower precedence. 

This mechanism makes it possible to invoke an existing Compose project with a custom set of variables as overrides, without the need to pass environment variables by the command line.

```console
$ cat .env
COMPOSE_FILE=../compose.yaml
POSTGRES_VERSION=9.3

$ cat ../compose.yaml 
services:
  db:
    image: "postgres:${POSTGRES_VERSION}"
$ cat ../.env
POSTGRES_VERSION=9.2

$ docker compose config
services:
  db:
    image: "postgres:9.3"
```

### Substitute from the shell 

You can use existing environment variables from your host machine or from the shell environment where you execute `docker compose` commands. This lets you dynamically inject values into your Docker Compose configuration at runtime.
For example, suppose the shell contains `POSTGRES_VERSION=9.3` and you supply the following configuration:

```yaml
db:
  image: "postgres:${POSTGRES_VERSION}"
```

When you run `docker compose up` with this configuration, Compose looks for the `POSTGRES_VERSION` environment variable in the shell and substitutes its value in. For this example, Compose resolves the image to `postgres:9.3` before running the configuration.

If an environment variable is not set, Compose substitutes with an empty string. In the previous example, if `POSTGRES_VERSION` is not set, the value for the image option is `postgres:`.

> [!NOTE]
>
> `postgres:` is not a valid image reference. Docker expects either a reference without a tag, like `postgres` which defaults to the latest image, or with a tag such as `postgres:15`.




---
## File: file-watch.md

---
description: Use File watch to automatically update running services as you work
keywords: compose, file watch, experimental
title: Use Compose Watch
weight: 50
aliases:
- /compose/file-watch/
---

{{< summary-bar feature_name="Compose file watch" >}}

{{% include "compose/watch.md" %}}

`watch` adheres to the following file path rules:
* All paths are relative to the project directory, apart from ignore file patterns
* Directories are watched recursively
* Glob patterns aren't supported
* Rules from `.dockerignore` apply
  * Use `ignore` option to define additional paths to be ignored (same syntax)
  * Temporary/backup files for common IDEs (Vim, Emacs, JetBrains, & more) are ignored automatically
  * `.git` directories are ignored automatically

You don't need to switch on `watch` for all services in a Compose project. In some instances, only part of the project, for example the Javascript frontend, might be suitable for automatic updates.

Compose Watch is designed to work with services built from local source code using the `build` attribute. It doesn't track changes for services that rely on pre-built images specified by the `image` attribute.

## Compose Watch versus bind mounts

Compose supports sharing a host directory inside service containers. Watch mode does not replace this functionality but exists as a companion specifically suited to developing in containers.

More importantly, `watch` allows for greater granularity than is practical with a bind mount. Watch rules let you ignore specific files or entire directories within the watched tree.

For example, in a JavaScript project, ignoring the `node_modules/` directory has two benefits:
* Performance. File trees with many small files can cause a high I/O load in some configurations
* Multi-platform. Compiled artifacts cannot be shared if the host OS or architecture is different from the container

For example, in a Node.js project, it's not recommended to sync the `node_modules/` directory. Even though JavaScript is interpreted, `npm` packages can contain native code that is not portable across platforms.

## Configuration

The `watch` attribute defines a list of rules that control automatic service updates based on local file changes.

Each rule requires a `path` pattern and `action` to take when a modification is detected. There are two possible actions for `watch` and depending on
the `action`, additional fields might be accepted or required. 

Watch mode can be used with many different languages and frameworks.
The specific paths and rules will vary from project to project, but the concepts remain the same. 

### Prerequisites

In order to work properly, `watch` relies on common executables. Make sure your service image contains the following binaries:
* stat
* mkdir
* rmdir

`watch` also requires that the container's `USER` can write to the target path so it can update files. A common pattern is for 
initial content to be copied into the container using the `COPY` instruction in a Dockerfile. To ensure such files are owned 
by the configured user, use the `COPY --chown` flag:

```dockerfile
# Run as a non-privileged user
FROM node:18
RUN useradd -ms /bin/sh -u 1001 app
USER app

# Install dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install

# Copy source files into application directory
COPY --chown=app:app . /app
```

### `action`

#### Sync

If `action` is set to `sync`, Compose makes sure any changes made to files on your host automatically match with the corresponding files within the service container.

`sync` is ideal for frameworks that support "Hot Reload" or equivalent functionality.

More generally, `sync` rules can be used in place of bind mounts for many development use cases.

#### Rebuild

If `action` is set to `rebuild`, Compose automatically builds a new image with BuildKit and replaces the running service container.

The behavior is the same as running `docker compose up --build <svc>`.

Rebuild is ideal for compiled languages or as a fallback for modifications to particular files that require a full
image rebuild (e.g. `package.json`).

> [!NOTE]
>
> When a service is rebuilt, the previous image version becomes dangling. By default, Compose removes these superseded dangling images after each rebuild to avoid accumulating unused layers. To keep them, use `docker compose watch --prune=false`.

#### Sync + Restart

If `action` is set to `sync+restart`, Compose synchronizes your changes with the service containers and restarts them. 

`sync+restart` is ideal when the config file changes, and you don't need to rebuild the image but just restart the main process of the service containers. 
It will work well when you update a database configuration or your `nginx.conf` file, for example.

>[!TIP]
>
> Optimize your `Dockerfile` for speedy
incremental rebuilds with [image layer caching](/build/cache)
and [multi-stage builds](/build/building/multi-stage/).

### `path` and `target`

The `target` field controls how the path is mapped into the container.

For `path: ./app/html` and a change to `./app/html/index.html`:

* `target: /app/html` -> `/app/html/index.html`
* `target: /app/static` -> `/app/static/index.html`
* `target: /assets` -> `/assets/index.html`

### `ignore`

The `ignore` patterns are relative to the `path` defined in the current `watch` action, not to the project directory. In the following Example 1, the ignore path would be relative to the `./web` directory specified in the `path` attribute.

### `initial_sync`

When using a `sync+x` action, the `initial_sync` attribute tells Compose to ensure files that are part of the defined `path` are up to date before starting a new watch session.

## Example 1

This minimal example targets a Node.js application with the following structure:
```text
myproject/
├── web/
│   ├── App.jsx
│   ├── index.js
│   └── node_modules/
├── Dockerfile
├── compose.yaml
└── package.json
```

```yaml
services:
  web:
    build: .
    command: npm start
    develop:
      watch:
        - action: sync
          path: ./web
          target: /src/web
          initial_sync: true
          ignore:
            - node_modules/
        - action: rebuild
          path: package.json
```

In this example, when running `docker compose up --watch`, a container for the `web` service is launched using an image built from the `Dockerfile` in the project's root.
The `web` service runs `npm start` for its command, which then launches a development version of the application with Hot Module Reload enabled in the bundler (Webpack, Vite, Turbopack, etc).

After the service is up, the watch mode starts monitoring the target directories and files.
Then, whenever a source file in the `web/` directory is changed, Compose syncs the file to the corresponding location under `/src/web` inside the container.
For example, `./web/App.jsx` is copied to `/src/web/App.jsx`.

Once copied, the bundler updates the running application without a restart.

And in this case, the `ignore` rule would apply to `myproject/web/node_modules/`, not `myproject/node_modules/`.

Unlike source code files, adding a new dependency can’t be done on-the-fly, so whenever `package.json` is changed, Compose
rebuilds the image and recreates the `web` service container.

This pattern can be followed for many languages and frameworks, such as Python with Flask: Python source files can be synced while a change to `requirements.txt` should trigger a rebuild.

## Example 2 

Adapting the previous example to demonstrate `sync+restart`:

```yaml
services:
  web:
    build: .
    command: npm start
    develop:
      watch:
        - action: sync
          path: ./web
          target: /app/web
          ignore:
            - node_modules/
        - action: sync+restart
          path: ./proxy/nginx.conf
          target: /etc/nginx/conf.d/default.conf

  backend:
    build:
      context: backend
      target: builder
```

This setup demonstrates how to use the `sync+restart` action in Docker Compose to efficiently develop and test a Node.js application with a frontend web server and backend service. The configuration ensures that changes to the application code and configuration files are quickly synchronized and applied, with the `web` service restarting as needed to reflect the changes.

## Use `watch`

{{% include "compose/configure-watch.md" %}}

> [!NOTE]
>
> Watch can also be used with the dedicated `docker compose watch` command if you don't want to 
> get the application logs mixed with the (re)build logs and filesystem sync events.

> [!TIP]
>
> Check out [`dockersamples/avatars`](https://github.com/dockersamples/avatars),
> or [local setup for Docker docs](https://github.com/docker/docs/blob/main/CONTRIBUTING.md)
> for a demonstration of Compose `watch`.

## Reference

- [Compose Develop Specification](/reference/compose-file/develop.md)


---
## File: gpu-support.md

---
description: Learn how to configure Docker Compose to use NVIDIA GPUs with CUDA-based containers
keywords: documentation, docs, docker, compose, GPU access, NVIDIA, samples
title: Run Docker Compose services with GPU access 
linkTitle: Enable GPU support
weight: 90
aliases:
- /compose/gpu-support/
---

Compose services can define GPU device reservations if the Docker host contains such devices and the Docker Daemon is set accordingly. For this, make sure you install the [prerequisites](/manuals/engine/containers/resource_constraints.md#gpu) if you haven't already done so.

The examples in the following sections focus specifically on providing service containers access to GPU devices with Docker Compose. 

## Enabling GPU access to service containers

GPUs are referenced in a `compose.yaml` file using the [device](/reference/compose-file/deploy.md#devices) attribute from the Compose Deploy specification, within your services that need them.

This provides more granular control over a GPU reservation as custom values can be set for the following device properties: 

- `capabilities`. This value is specified as a list of strings. For example, `capabilities: [gpu]`. You must set this field in the Compose file. Otherwise, it returns an error on service deployment.
- `count`. Specified as an integer or the value `all`, represents the number of GPU devices that should be reserved (providing the host holds that number of GPUs). If `count` is set to `all` or not specified, all GPUs available on the host are used by default.
- `device_ids`. This value, specified as a list of strings, represents GPU device IDs from the host. You can find the device ID in the output of `nvidia-smi` on the host. If no `device_ids` are set, all GPUs available on the host are used by default.
- `driver`. Specified as a string, for example `driver: 'nvidia'`
- `options`. Key-value pairs representing driver specific options.


> [!IMPORTANT]
>
> You must set the `capabilities` field. Otherwise, it returns an error on service deployment.

> [!NOTE]
>
> `count` and `device_ids` are mutually exclusive. You must only define one field at a time.

For more information on these properties, see the [Compose Deploy Specification](/reference/compose-file/deploy.md#devices).

### Example of a Compose file for running a service with access to 1 GPU device

```yaml
services:
  test:
    image: nvidia/cuda:12.9.0-base-ubuntu22.04
    command: nvidia-smi
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

Run with Docker Compose:

```console
$ docker compose up
Creating network "gpu_default" with the default driver
Creating gpu_test_1 ... done
Attaching to gpu_test_1    
test_1  | +-----------------------------------------------------------------------------+
test_1  | | NVIDIA-SMI 450.80.02    Driver Version: 450.80.02    CUDA Version: 11.1     |
test_1  | |-------------------------------+----------------------+----------------------+
test_1  | | GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
test_1  | | Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
test_1  | |                               |                      |               MIG M. |
test_1  | |===============================+======================+======================|
test_1  | |   0  Tesla T4            On   | 00000000:00:1E.0 Off |                    0 |
test_1  | | N/A   23C    P8     9W /  70W |      0MiB / 15109MiB |      0%      Default |
test_1  | |                               |                      |                  N/A |
test_1  | +-------------------------------+----------------------+----------------------+
test_1  |                                                                                
test_1  | +-----------------------------------------------------------------------------+
test_1  | | Processes:                                                                  |
test_1  | |  GPU   GI   CI        PID   Type   Process name                  GPU Memory |
test_1  | |        ID   ID                                                   Usage      |
test_1  | |=============================================================================|
test_1  | |  No running processes found                                                 |
test_1  | +-----------------------------------------------------------------------------+
gpu_test_1 exited with code 0

```

On machines hosting multiple GPUs, the `device_ids` field can be set to target specific GPU devices and `count` can be used to limit the number of GPU devices assigned to a service container. 

You can use `count` or `device_ids` in each of your service definitions. An error is returned if you try to combine both, specify an invalid device ID, or use a value of count that’s higher than the number of GPUs in your system.

```console
$ nvidia-smi   
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 450.80.02    Driver Version: 450.80.02    CUDA Version: 11.0     |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|                               |                      |               MIG M. |
|===============================+======================+======================|
|   0  Tesla T4            On   | 00000000:00:1B.0 Off |                    0 |
| N/A   72C    P8    12W /  70W |      0MiB / 15109MiB |      0%      Default |
|                               |                      |                  N/A |
+-------------------------------+----------------------+----------------------+
|   1  Tesla T4            On   | 00000000:00:1C.0 Off |                    0 |
| N/A   67C    P8    11W /  70W |      0MiB / 15109MiB |      0%      Default |
|                               |                      |                  N/A |
+-------------------------------+----------------------+----------------------+
|   2  Tesla T4            On   | 00000000:00:1D.0 Off |                    0 |
| N/A   74C    P8    12W /  70W |      0MiB / 15109MiB |      0%      Default |
|                               |                      |                  N/A |
+-------------------------------+----------------------+----------------------+
|   3  Tesla T4            On   | 00000000:00:1E.0 Off |                    0 |
| N/A   62C    P8    11W /  70W |      0MiB / 15109MiB |      0%      Default |
|                               |                      |                  N/A |
+-------------------------------+----------------------+----------------------+
```

## Access specific devices

To allow access only to GPU-0 and GPU-3 devices:

```yaml
services:
  test:
    image: tensorflow/tensorflow:latest-gpu
    command: python -c "import tensorflow as tf;tf.test.gpu_device_name()"
    deploy:
      resources:
        reservations:
          devices:
          - driver: nvidia
            device_ids: ['0', '3']
            capabilities: [gpu]

```


---
## File: _index.md

---
build:
  render: never
title: How-tos
weight: 40
---

---
## File: init-containers.md

---
title: Use init containers in Compose
linkTitle: Use init containers
weight: 120
description: Use pre_start init containers to run setup tasks before a service starts in Docker Compose.
keywords: docker compose init containers, pre_start, docker compose migrations, volume permissions, docker compose lifecycle
params:
  sidebar:
    badge:
      color: green
      text: New
---

{{< summary-bar feature_name="Compose pre_start" >}}

Init containers are short-lived containers that run before a service's main container starts. They execute sequentially, each running to completion before the next begins. If any step exits with a non-zero code, the service will not start.

Use them for setup work that must finish before the application boots: running database migrations, fixing volume permissions, generating dynamic configuration, or executing any ordered sequence of prerequisites.

Compose models init containers as [`pre_start`](/reference/compose-file/services.md#pre_start) lifecycle hooks. Unlike [`post_start`](/reference/compose-file/services.md#post_start) and [`pre_stop`](/reference/compose-file/services.md#pre_stop), which run a command inside the running service container, each `pre_start` step runs in its own ephemeral container created after the service container is created but before it is started.

## When not to use init containers

For static files and secrets, use the native [`configs`](/reference/compose-file/configs.md) and [`secrets`](/reference/compose-file/secrets.md) top-level elements instead. Compose mounts them directly into containers with a configurable target path, mode, UID, and GID. No init container required.

For background tasks with their own lifecycle - scheduled backups, post-exit cleanup, periodic maintenance — init containers are the wrong tool. Those tasks run independently of service startup, not before it.

## How `pre_start` containers run

Each step in a service's `pre_start` list:

- Runs in its own ephemeral container, created after the service container is created but before it starts.
- Inherits the service's image by default. Set `image` to override. The hook image follows the parent service's `pull_policy`, including refresh interval (`daily`, `weekly`, `every_<duration>`). This applies when starting services and when running `docker compose pull`.
- Joins the same networks as the service, so it can reach services declared in [`depends_on`](/reference/compose-file/services.md#depends_on).
- Shares the service's volume mounts, so files written to a shared volume are immediately visible to the service.
- Must exit `0` for the next step, and the service itself, to start. A non-zero exit aborts startup for the service and anything that depends on it.

A `pre_start` step is skipped on subsequent `docker compose up` runs if it previously succeeded, its definition hasn't changed, or when the service container restarts under its `restart` policy. It reruns if the definition changes, the previous run failed, or the service is recreated with `--force-recreate`.

## Examples

### Run a database migration before the app starts

In the following example, `app` waits for `db` to be healthy, then runs
`./manage.py migrate` in an ephemeral container that reuses the app's
image. The service container only starts once the migration exits `0`.

```yaml
services:
  app:
    image: myapp:latest
    depends_on:
      db:
        condition: service_healthy
    pre_start:
      - command: ["./manage.py", "migrate"]

  db:
    image: postgres:18
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 10s
      retries: 5
      start_period: 30s
      timeout: 10s
```

If the migration fails, `app` does not start and the failure is reported in
the `docker compose up` output.

### Fix volume ownership before a non-root service starts

Named volumes are created with root ownership. When the service runs as a
non-root user, you can use a `pre_start` step to adjust ownership before
the service mounts the volume.

```yaml
services:
  app:
    image: myapp:latest
    user: "1000:1000"
    volumes:
      - data:/data
    pre_start:
      - image: busybox
        user: root
        command: sh -c 'chown -R 1000:1000 /data'

volumes:
  data:
```

The `pre_start` step uses a different image (`busybox`) and runs as `root`,
even though the service itself runs as user `1000`.

### Chain multiple setup steps

`pre_start` steps run in declared order. The next step only starts once the
previous one exits `0`. In the following example, the application waits
for migrations to finish, then for seed data to load, before starting.

```yaml
services:
  app:
    image: myapp:latest
    depends_on:
      db:
        condition: service_healthy
    pre_start:
      - command: ["./manage.py", "migrate"]
      - command: ["./manage.py", "loaddata", "fixtures.json"]

  db:
    image: postgres:18
```

Each step runs in its own ephemeral container. If the second step fails,
the first step is not rolled back, but `app` does not start.

### Replace the one-shot service pattern

Before `pre_start`, the common way to express "run X before Y starts" was
to model the setup work as a service with `restart: "no"` and have the main
service `depends_on` it with `condition: service_completed_successfully`:

```yaml
services:
  migrate:
    image: myapp:latest
    command: ["./manage.py", "migrate"]
    restart: "no"

  app:
    image: myapp:latest
    depends_on:
      migrate:
        condition: service_completed_successfully
```

The equivalent expressed with `pre_start`:

```yaml
services:
  app:
    image: myapp:latest
    pre_start:
      - command: ["./manage.py", "migrate"]
```

`pre_start` is preferable because:

- The setup work is modeled as a subordinate step of the service, not as a peer service that exits immediately.
- Completed steps do not appear as exited services in `docker compose ps`.
- Chaining several setup steps does not require a web of `depends_on` edges between one-shot services.
- The ephemeral container inherits the service's image by default, so no duplicate `image:` declaration is needed.

The one-shot service pattern still has its place when the setup work is a shared concern that multiple services depend on, or when it needs to be addressable independently of any single service.

## Limitations

- `pre_start` runs once for the service as a whole, not once per replica (`per_replica: false`). Per-replica execution (`per_replica: true`) is not yet supported.
- Volume mounts shared across replicas (named volumes, bind mounts) are accessible from a `pre_start` step. Per-instance mounts such as `tmpfs`
  or anonymous volumes cannot be addressed by a single shared run.
- `pre_start` does not re-trigger when you scale a service up. A step runs again only on definition change, prior failure, or `--force-recreate`.

## Reference and additional information

- [`pre_start`](/reference/compose-file/services.md#pre_start)
- [`post_start`](/reference/compose-file/services.md#post_start)
- [`pre_stop`](/reference/compose-file/services.md#pre_stop)
- [`depends_on`](/reference/compose-file/services.md#depends_on)
- [Use lifecycle hooks](/manuals/compose/how-tos/lifecycle.md)
- [Control startup order](/manuals/compose/how-tos/startup-order.md)


---
## File: lifecycle.md

---
title: Using lifecycle hooks with Compose
linkTitle: Use lifecycle hooks
weight: 110
description: Learn how to use Docker Compose lifecycle hooks like pre_start, post_start, and pre_stop to customize container behavior.
keywords: docker compose lifecycle hooks, post_start, pre_stop, pre_start, docker compose entrypoint, docker container stop hooks, compose hook commands
---

{{< summary-bar feature_name="Compose lifecycle hooks" >}}

## Services lifecycle hooks

When Docker Compose runs a container, it uses two elements, 
[ENTRYPOINT and COMMAND](/manuals/engine/containers/run.md#default-command-and-options), 
to manage what happens when the container starts and stops.

However, it can sometimes be easier to handle these tasks separately with lifecycle hooks - 
commands that run right after the container starts or just before it stops.

Lifecycle hooks are particularly useful because they can have special privileges 
(like running as the root user), even when the container itself runs with lower privileges 
for security. This means that certain tasks requiring higher permissions can be done without 
compromising the overall security of the container.

### Post-start hooks

Post-start hooks are commands that run after the container has started, but there's no 
set time for when exactly they will execute. The hook execution timing is not assured during 
the execution of the container's `entrypoint`.

Because there is no ordering guarantee between the hook and the container's entrypoint,
post-start hooks are best suited for tasks that do not need to complete before the
application begins running, such as registering the container with an external system.

In the following example, after the container starts, a root-level hook registers the
service with an internal service registry. The application does not depend on registration
being complete before it starts serving requests.

```yaml
services:
  app:
    image: backend
    user: 1001
    post_start:
      - command: /opt/scripts/register-service.sh
        user: root
```

### Pre-stop hooks

Pre-stop hooks are commands that run before the container is stopped by a specific 
command (like `docker compose down` or stopping it manually with `Ctrl+C`). 
These hooks won't run if the container stops by itself or gets killed suddenly.

Because the pre-stop hook runs before the stop signal is sent to the container, it is
suited for actions that must complete while the application is still fully running.

In the following example, the hook backs up a data file before the container receives the stop signal.

```yaml
services:
  app:
    image: backend
    volumes:
      - data:/data
    pre_stop:
      - command: cp /data/app.db /data/app.db.bak

volumes:
  data: {} # a Docker volume is created with root ownership
```

## Reference information

- [`post_start`](/reference/compose-file/services.md#post_start)
- [`pre_stop`](/reference/compose-file/services.md#pre_stop)


---
## File: extends.md

---
description: Learn how to reuse service configurations across files and projects using Docker Compose’s extends attribute.
keywords: fig, composition, compose, docker, orchestration, documentation, docs, compose file modularization
title: Extend your Compose file
linkTitle: Extend
weight: 20
aliases:
- /compose/extends/
---

Docker Compose's [`extends` attribute](/reference/compose-file/services.md#extends)
lets you share common configurations among different files, or even different
projects entirely.

Extending services is useful if you have several services that reuse a common
set of configuration options. With `extends` you can define a common set of
service options in one place and refer to it from anywhere. You can refer to
another Compose file and select a service you want to also use in your own
application, with the ability to override some attributes for your own needs.

> [!IMPORTANT]
>
> When you use multiple Compose files, you must make sure all paths in the files
are relative to the base Compose file (i.e. the Compose file in your main-project folder). This is required because extend files
need not be valid Compose files. Extend files can contain small fragments of
configuration. Tracking which fragment of a service is relative to which path is
difficult and confusing, so to keep paths easier to understand, all paths must
be defined relative to the base file. 

> [!NOTE]
>
> `extends` is not supported when deploying with `docker stack deploy`. Running
> `docker stack config` on a Compose file that uses `extends` returns the error:
> `Configuration contains forbidden properties`.

## How the `extends` attribute works

### Extending services from another file

Take the following example:

```yaml
services:
  web:
    extends:
      file: common-services.yml
      service: webapp
```

This instructs Compose to reuse only the properties of the `webapp` service
defined in the `common-services.yml` file. The `webapp` service itself is not part of the final project.

If `common-services.yml`
looks like this:

```yaml
services:
  webapp:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - "/data"
```
You get exactly the same result as if you wrote
`compose.yaml` with the same `build`, `ports`, and `volumes` configuration
values defined directly under `web`.

To include the service `webapp` in the final project when extending services from another file, you need to explicitly include both services in your current Compose file. For example (this is for illustrative purposes only):

```yaml
services:
  web:
    build: ./alpine
    command: echo
    extends:
      file: common-services.yml
      service: webapp
  webapp:
    extends:
      file: common-services.yml
      service: webapp
```

Alternatively, you can use [include](include.md). 

### Extending services within the same file 

If you define services in the same Compose file and extend one service from another, both the original service and the extended service will be part of your final configuration. For example:

```yaml 
services:
  web:
    build: ./alpine
    extends: webapp
  webapp:
    environment:
      - DEBUG=1
```

### Extending services within the same file and from another file

You can go further and define, or re-define, configuration locally in
`compose.yaml`:

```yaml
services:
  web:
    extends:
      file: common-services.yml
      service: webapp
    environment:
      - DEBUG=1
    cpu_shares: 5

  important_web:
    extends: web
    cpu_shares: 10
```

## Additional example

Extending an individual service is useful when you have multiple services that
have a common configuration. The example below is a Compose app with two
services, a web application and a queue worker. Both services use the same
codebase and share many configuration options.

The `common.yaml` file defines the common configuration:

```yaml
services:
  app:
    build: .
    environment:
      CONFIG_FILE_PATH: /code/config
      API_KEY: xxxyyy
    cpu_shares: 5
```

The `compose.yaml` defines the concrete services which use the common
configuration:

```yaml
services:
  webapp:
    extends:
      file: common.yaml
      service: app
    command: /code/run_web_app
    ports:
      - 8080:8080
    depends_on:
      - queue
      - db

  queue_worker:
    extends:
      file: common.yaml
      service: app
    command: /code/run_worker
    depends_on:
      - queue
```

## Relative paths

When using `extends` with a `file` attribute which points to another folder, relative paths 
declared by the service being extended are converted so they still point to the
same file when used by the extending service. This is illustrated in the following example:

Base Compose file:
```yaml
services:
  webapp:
    image: example
    extends:
      file: ../commons/compose.yaml
      service: base
```

The `commons/compose.yaml` file:
```yaml
services:
  base:
    env_file: ./container.env
```

The resulting service refers to the original `container.env` file
within the `commons` directory. This can be confirmed with `docker compose config`
which inspects the actual model:
```yaml
services:
  webapp:
    image: example
    env_file: 
      - ../commons/container.env
```

## Reference information

- [`extends`](/reference/compose-file/services.md#extends)


---
## File: include.md

---
description: How to use Docker Compose's include top-level element
keywords: compose, docker, include, compose file
title: Include
---

{{< summary-bar feature_name="Compose include" >}}

{{% include "compose/include.md" %}}

The [`include` top-level element](/reference/compose-file/include.md) helps to reflect the engineering team responsible for the code directly in the config file's organization. It also solves the relative path problem that [`extends`](extends.md) and [merge](merge.md) present. 

Each path listed in the `include` section loads as an individual Compose application model, with its own project directory, in order to resolve relative paths.

Once the included Compose application loads, all resources are copied into the current Compose application model.

> [!NOTE]
>
> `include` applies recursively so an included Compose file which declares its own `include` section, causes those files to also be included.

## Example

```yaml
include:
  - my-compose-include.yaml  #with serviceB declared
services:
  serviceA:
    build: .
    depends_on:
      - serviceB #use serviceB directly as if it was declared in this Compose file
```

`my-compose-include.yaml` manages `serviceB` which details some replicas, web UI to inspect data, isolated networks, volumes for data persistence, etc. The application relying on `serviceB` doesn’t need to know about the infrastructure details, and consumes the Compose file as a building block it can rely on. 

This means the team managing `serviceB` can refactor its own database component to introduce additional services without impacting any dependent teams. It also means that the dependent teams don't need to include additional flags on each Compose command they run.

```yaml
include:
  - oci://docker.io/username/my-compose-app:latest # use a Compose file stored as an OCI artifact
services:
  serviceA:
    build: .
    depends_on:
      - serviceB 
```
`include` allows you to reference Compose files from remote sources, such as OCI artifacts or Git repositories.  
Here `serviceB` is defined in a Compose file stored on Docker Hub.

## Using overrides with included Compose files

Compose reports an error if any resource from `include` conflicts with resources from the included Compose file. This rule prevents
unexpected conflicts with resources defined by the included compose file author. However, there may be some circumstances where you might want to customize the
included model. This can be achieved by adding an override file to the include directive:

```yaml
include:
  - path : 
      - third-party/compose.yaml
      - override.yaml  # local override for third-party model
```

The main limitation with this approach is that you need to maintain a dedicated override file per include. For complex projects with multiple
includes this would result in many Compose files.

The other option is to use a `compose.override.yaml` file. While conflicts will be rejected from the file using `include` when same
resource is declared, a global Compose override file can override the resulting merged model, as demonstrated in following example:

Main `compose.yaml` file:
```yaml
include:
  - team-1/compose.yaml # declare service-1
  - team-2/compose.yaml # declare service-2
```

Override `compose.override.yaml` file:
```yaml
services:
  service-1:
    # override included service-1 to enable debugger port
    ports:
      - 2345:2345

  service-2:
    # override included service-2 to use local data folder containing test data
    volumes:
      - ./data:/data
```

Combined together, this allows you to benefit from third-party reusable components, and adjust the Compose model for your needs.

## Reference information

[`include` top-level element](/reference/compose-file/include.md)


---
## File: _index.md

---
description: General overview for the different ways you can work with multiple compose
  files in Docker Compose
keywords: compose, compose file, merge, extends, include, docker compose, -f flag
linkTitle: Use multiple Compose files
title: Use multiple Compose files
weight: 80
aliases:
- /compose/multiple-compose-files/
---

This section contains information on the ways you can work with multiple Compose files. 

Using multiple Compose files lets you customize a Compose application for different environments or workflows. This is useful for large applications that may use dozens of containers, with ownership distributed across multiple teams. For example, if your organization or team uses a monorepo, each team may have their own “local” Compose file to run a subset of the application. They then need to rely on other teams to provide a reference Compose file that defines the expected way to run their own subset. Complexity moves from the code in to the infrastructure and the configuration file.

The simplest way to work with multiple Compose files is to [merge](merge.md) them using
the `-f` flag. This works well for straightforward overrides, but the
[merging rules](merge.md#merging-rules) can make it complex to manage as your
configuration grows.

Docker Compose provides two other options to manage this complexity when working with multiple Compose files. Depending on your project's needs, you can: 

- [Extend a Compose file](extends.md) by referring to another Compose file and selecting the bits you want to use in your own application, with the ability to override some attributes.
- [Include other Compose files](include.md) directly in your Compose file.



---
## File: merge.md

---
description: How merging Compose files works
keywords: compose, docker, merge, compose file
title: Merge Compose files
linkTitle: Merge
weight: 10
---

Docker Compose lets you merge and override a set of Compose files together to create a composite Compose file.

By default, Compose reads two files, a `compose.yaml` and an optional
`compose.override.yaml` file. By convention, the `compose.yaml`
contains your base configuration. The override file can
contain configuration overrides for existing services or entirely new
services.

If a service is defined in both files, Compose merges the configurations using
the rules described below and in the 
[Compose Specification](/reference/compose-file/merge.md).

## How to merge multiple Compose files

To use multiple override files, or an override file with a different name, you
can either use the pre-defined [COMPOSE_FILE](../environment-variables/envvars.md#compose_file) environment variable, or use the `-f` option to specify the list of files. 

Compose merges files in
the order they're specified on the command line. Subsequent files may merge, override, or
add to their predecessors.

For example:

```console
$ docker compose -f compose.yaml -f compose.admin.yaml run backup_db
```

The `compose.yaml` file might specify a `webapp` service.

```yaml
webapp:
  image: examples/web
  ports:
    - "8000:8000"
  volumes:
    - "/data"
```

The `compose.admin.yaml` may also specify this same service: 

```yaml
webapp:
  environment:
    - DEBUG=1
```

Any matching
fields override the previous file. New values, add to the `webapp` service
configuration:

```yaml
webapp:
  image: examples/web
  ports:
    - "8000:8000"
  volumes:
    - "/data"
  environment:
    - DEBUG=1
```

## Merging rules 

- Paths are evaluated relative to the base file. When you use multiple Compose files, you must make sure all paths in the files are relative to the base Compose file (the first Compose file specified
with `-f`). This is required because override files need not be valid
Compose files. Override files can contain small fragments of configuration.
Tracking which fragment of a service is relative to which path is difficult and
confusing, so to keep paths easier to understand, all paths must be defined
relative to the base file.

   >[!TIP]
   >
   > You can use `docker compose config` to review your merged configuration and avoid path-related issues.

- Compose copies configurations from the original service over to the local one.
If a configuration option is defined in both the original service and the local
service, the local value replaces or extends the original value.

   - For single-value options like `image`, `command` or `mem_limit`, the new value replaces the old value.

      original service:

      ```yaml
      services:
        myservice:
          # ...
          command: python app.py
      ```

      local service:

      ```yaml
      services:
        myservice:
          # ...
          command: python otherapp.py
      ```

      result:

      ```yaml
      services:
        myservice:
          # ...
          command: python otherapp.py
      ```

   - For the multi-value options `ports`, `expose`, `external_links`, `dns`, `dns_search`, and `tmpfs`, Compose concatenates both sets of values:

      original service:

      ```yaml
      services:
        myservice:
          # ...
          expose:
            - "3000"
      ```

      local service:

      ```yaml
      services:
        myservice:
          # ...
          expose:
            - "4000"
            - "5000"
      ```

      result:

      ```yaml
      services:
        myservice:
          # ...
          expose:
            - "3000"
            - "4000"
            - "5000"
      ```

   - In the case of `environment`, `labels`, `volumes`, and `devices`, Compose "merges" entries together with locally defined values taking precedence. For `environment` and `labels`, the environment variable or label name determines which value is used:

      original service:

      ```yaml
      services:
        myservice:
          # ...
          environment:
            - FOO=original
            - BAR=original
      ```

      local service:

      ```yaml
      services:
        myservice:
          # ...
          environment:
            - BAR=local
            - BAZ=local
      ```

     result:

      ```yaml
      services:
        myservice:
          # ...
          environment:
            - FOO=original
            - BAR=local
            - BAZ=local
      ```

   - Entries for `volumes` and `devices` are merged using the mount path in the container:

      original service:

      ```yaml
      services:
        myservice:
          # ...
          volumes:
            - ./original:/foo
            - ./original:/bar
      ```

      local service:

      ```yaml
      services:
        myservice:
          # ...
          volumes:
            - ./local:/bar
            - ./local:/baz
      ```

      result:

      ```yaml
      services:
        myservice:
          # ...
          volumes:
            - ./original:/foo
            - ./local:/bar
            - ./local:/baz
      ```

For more merging rules, see [Merge and override](/reference/compose-file/merge.md) in the Compose Specification. 

### Additional information

- Using `-f` is optional. If not provided, Compose searches the working directory and its parent directories for a `compose.yaml` and a `compose.override.yaml` file. You must supply at least the `compose.yaml` file. If both files exist on the same directory level, Compose combines them into a single configuration.

- You can use a `-f` with `-` (dash) as the filename to read the configuration from `stdin`. For example: 
   ```console
   $ docker compose -f - <<EOF
     webapp:
       image: examples/web
       ports:
        - "8000:8000"
       volumes:
        - "/data"
       environment:
        - DEBUG=1
     EOF
   ```
   
   When `stdin` is used, all paths in the configuration are relative to the current working directory.
   
- You can use the `-f` flag to specify a path to a Compose file that is not located in the current directory, either from the command line or by setting up a [COMPOSE_FILE environment variable](../environment-variables/envvars.md#compose_file) in your shell or in an environment file.

   For example, if you are running the [Compose Rails sample](https://github.com/docker/awesome-compose/tree/master/official-documentation-samples/rails/README.md), and have a `compose.yaml` file in a directory called `sandbox/rails`. You can use a command like [docker compose pull](/reference/cli/docker/compose/pull/) to get the postgres image for the `db` service from anywhere by using the `-f` flag as follows: `docker compose -f ~/sandbox/rails/compose.yaml pull db`

   Here's the full example:

   ```console
   $ docker compose -f ~/sandbox/rails/compose.yaml pull db
   Pulling db (postgres:18)...
   18: Pulling from library/postgres
   ef0380f84d05: Pull complete
   50cf91dc1db8: Pull complete
   d3add4cd115c: Pull complete
   467830d8a616: Pull complete
   089b9db7dc57: Pull complete
   6fba0a36935c: Pull complete
   81ef0e73c953: Pull complete
   338a6c4894dc: Pull complete
   15853f32f67c: Pull complete
   044c83d92898: Pull complete
   17301519f133: Pull complete
   dcca70822752: Pull complete
   cecf11b8ccf3: Pull complete
   Digest: sha256:1364924c753d5ff7e2260cd34dc4ba05ebd40ee8193391220be0f9901d4e1651
   Status: Downloaded newer image for postgres:18
   ```

## Example

A common use case for multiple files is changing a development Compose app
for a production-like environment (which may be production, staging or CI).
To support these differences, you can split your Compose configuration into
a few different files:

Start with a base file that defines the canonical configuration for the
services.

`compose.yaml`

```yaml
services:
  web:
    image: example/my_web_app:latest
    depends_on:
      - db
      - cache

  db:
    image: postgres:18

  cache:
    image: redis:latest
```

In this example the development configuration exposes some ports to the
host, mounts our code as a volume, and builds the web image.

`compose.override.yaml`

```yaml
services:
  web:
    build: .
    volumes:
      - '.:/code'
    ports:
      - 8883:80
    environment:
      DEBUG: 'true'

  db:
    command: '-d'
    ports:
     - 5432:5432

  cache:
    ports:
      - 6379:6379
```

When you run `docker compose up` it reads the overrides automatically.

To use this Compose app in a production environment, another override file is created, which might be stored in a different git
repository or managed by a different team.

`compose.prod.yaml`

```yaml
services:
  web:
    ports:
      - 80:80
    environment:
      PRODUCTION: 'true'

  cache:
    environment:
      TTL: '500'
```

To deploy with this production Compose file you can run

```console
$ docker compose -f compose.yaml -f compose.prod.yaml up -d
```

This deploys all three services using the configuration in
`compose.yaml` and `compose.prod.yaml` but not the
dev configuration in `compose.override.yaml`.

For more information, see [Using Compose in production](../production.md). 

## Limitations

When merging Compose files, all relative paths (for build contexts, environment files,
bind-mounted volumes, and other resources) are resolved relative to the base Compose file. The
first file specified with `-f`, or `compose.yaml` in the current directory if `-f` is
not used. Paths in override files are not resolved relative to the override file's own
location.

This means that in a monorepo where Compose files are spread across team or component
subdirectories, relative paths in those files are resolved incorrectly when used as
override files.

> [!TIP] 
>
> If you need each Compose file's paths to resolve relative to its own location,
> use the [`include` top-level element](include.md) instead of merging with `-f`. Each
> included file is loaded with its own project directory, so relative paths resolve
> correctly.

## Reference information

- [Merge rules](/reference/compose-file/merge.md)


---
## File: networking.md

---
description: How Docker Compose sets up networking between containers
keywords: documentation, docs, docker, compose, orchestration, containers, networking
title: Networking in Compose
linkTitle: Networking
weight: 70
aliases:
  - /compose/networking/
---

Compose handles networking for you by default, but gives you fine-grained control when you need it. This page explains how the default network works and how containers discover each other by name. It also covers when and how to define custom networks, connect services across separate Compose projects, map custom hostnames, and debug connectivity issues.

## Default network and service discovery

By default, Compose sets up a single [network](/reference/cli/docker/network/create/) for your app. Each container for a service joins the default network and is both reachable by other containers on that network, and discoverable by its service name. This network uses the `bridge` driver. To attach services to a different Compose network or an external one, see [Specify custom networks](#specify-custom-networks). To change how a service uses the host network stack (`network_mode: host`), see [Change the network mode](#change-the-network-mode).

For most development setups, the default network is sufficient. When you run `docker compose up`, Compose creates a network named `<project-name>_default` and attaches all services to it. Each service registers its name with an internal DNS server, so containers can reach each other using the service name directly. No IP addresses or manual configuration is needed.

For example, suppose your app is in a directory called `myapp`, and your `compose.yaml` looks like this:

```yaml
services:
  web:
    build: .
    ports:
      - "8000:8000"
  db:
    image: postgres:latest
    ports:
      - "8001:5432"
```

Compose automatically connects all services to the default network, so you don't need to define `networks` explicitly in the Compose file.

When you run `docker compose up`, the following happens:

1. A network called `myapp_default` is created.
2. A container is created using `web`'s configuration. It joins `myapp_default` under the name `web`.
3. A container is created using `db`'s configuration. It joins `myapp_default` under the name `db`.

Each container can now look up the service name `web` or `db` and get back the appropriate container's IP address. The `web` service can connect to the database at `postgres://db:5432`. From the host machine, the same database is accessible at `postgres://localhost:8001` if your container is running locally.

> [!TIP]
>
> Docker assigns container IP addresses dynamically from the network's subnet each time a container starts so they are not persisted across restarts or recreations. This means you should always reference services by name, not IP address. When containers are recreated, for example after a configuration change, they receive a new IP address. The service name stays stable.

Your app's network is given a name based on the "project name", which is taken from the name of the directory it lives in. You can override the project name with either the [`--project-name` flag](/reference/cli/docker/compose/) or the [`COMPOSE_PROJECT_NAME` environment variable](environment-variables/envvars.md#compose_project_name).

The `HOST_PORT` and `CONTAINER_PORT` serve different purposes. In the example above, for `db`, the `HOST_PORT` is `8001` and the container port is `5432` (the Postgres default). Networked service-to-service communication uses the `CONTAINER_PORT`. The host port is only used when accessing the service from outside the network.

### Updating containers on the network

If you make a configuration change to a service and run `docker compose up` to update it, the old container is removed and the new one joins the network under a different IP address but the same name. Running containers can look up that name and connect to the new address, but the old address stops working.

If any containers have connections open to the old container, they are closed. It is each container's responsibility to detect this condition, look up the name again, and reconnect.

## Change the network mode

By default, each service joins the project's bridge network. It is the most secure networking mode. If you don't specify [`network_mode`](/reference/compose-file/services.md#network_mode), this is the type of network you are creating.

You can override the networking mode on a per-service basis. The `network_mode` option accepts the following values:

- `host`: The container shares the host's network stack. No port mapping is needed or supported, and service name DNS resolution does not work. Use for system-level tools like network monitors that require direct access to host interfaces. A container using `network_mode: host` can access all host ports and observe all network traffic on the host. Use it only when genuinely required.
- `none`: Turns off all container networking.
- `service:{name}`: Gives the container access to the specified container by referring to its service name.
- `container:{name}`: Gives the container access to the specified container by referring to its container ID.

You can mix modes in a single project:

```yaml
services:
  app:
    image: myapp
    networks:
      - isolated
    ports:
      - "3000:3000"

  monitoring:
    image: netdata/netdata
    network_mode: host   # Can monitor host system and all host ports

networks:
  isolated:
    driver: bridge
```

## Specify custom networks

Instead of just using the default app network, you can specify your own networks with the top-level `networks` key. This lets you create more complex topologies and specify [custom network drivers](/engine/extend/plugins_network/) and options. You can also use it to connect services to externally-created networks which aren't managed by Compose.

Each service can specify what networks to connect to with the service-level `networks` key, which is a list of names referencing entries under the top-level `networks` key.

The following example shows a Compose file which defines two custom networks. The `proxy` service is isolated from the `db` service, because they do not share a network in common. Only `app` can talk to both.

```yaml
services:
  proxy:
    build: ./proxy
    networks:
      - frontend
  app:
    build: ./app
    networks:
      - frontend
      - backend
  db:
    image: postgres:latest
    networks:
      - backend

networks:
  frontend:
    driver: bridge   # Specify driver options
    driver_opts:
      com.docker.network.bridge.host_binding_ipv4: "127.0.0.1"
  backend:
    driver: custom-driver  # Use a custom driver
```

Networks can be configured with static IP addresses by setting the [ipv4_address and/or ipv6_address](/reference/compose-file/services.md#ipv4_address-ipv6_address) for each attached network.

Networks can also be given a [custom name](/reference/compose-file/networks.md#name):

```yaml
services:
  # ...
networks:
  frontend:
    name: custom_frontend
    driver: custom-driver-1
```

### Internal networks

Setting `internal: true` on a network creates it without a connection to the host's network interfaces. It has no default gateway for external connectivity. This is useful for services like databases that should be completely unreachable from outside the container network:

```yaml
services:
  cache:
    image: redis
    networks:
      - isolated

  worker:
    image: myworker
    networks:
      - isolated
      - public

networks:
  isolated:
    internal: true   # No external connectivity
  public:   # Standard bridge network, created by Compose on docker compose up
```

Note that a service connected to both an internal and a non-internal network (like `worker` above) can still reach the internet via the non-internal network `public`.

### Configure the default network

Instead of, or as well as, specifying your own networks, you can also change the settings of the app-wide default network by defining an entry under `networks` named `default`:

```yaml
services:
  web:
    build: .
    ports:
      - "8000:8000"
  db:
    image: postgres:latest

networks:
  default:
    driver: custom-driver-1   # Use a custom driver
```

## Use an existing external network

If you've manually created a bridge network using `docker network create`, you can connect your Compose services to it by marking the network as [`external`](/reference/compose-file/networks.md#external):

```yaml
services:
  # ...
networks:
  network1:
    name: my-pre-existing-network
    external: true
```

Instead of creating `<project-name>_default`, Compose looks for a network called `my-pre-existing-network` and connects your containers to it.

### Connecting multiple Compose projects

External networks are particularly useful when services in separate Compose projects need to communicate. Create a shared network once, then reference it as external in each project:

```bash
docker network create inter-project
```

backend-compose.yaml:

```yaml
services:
  api:
    image: myapi:latest
    networks:
      - shared
      - default   # Also keep the project's internal network

networks:
  shared:
    external: true
    name: inter-project
```

frontend-compose.yaml:

```yaml
services:
  web:
    image: myfrontend:latest
    environment:
      API_URL: http://api:8080   # Reference by service name
    networks:
      - shared

networks:
  shared:
    external: true
    name: inter-project
```

Services on the same external network can reach each other by service name, just like services within a single project.

> [!IMPORTANT]
>
> The external network must exist before you run `docker compose up`. If it doesn't, Compose fails with a `Network not found` error. Always create it first with `docker network create`.

## Hybrid networking

A service can belong to both an external shared network and its own project-internal network. This lets you expose only the services that need to be reachable from other projects, while keeping everything else, such as databases, fully isolated:

```yaml
services:
  api:
    image: myapp-api
    networks:
      - shared     # Reachable from other projects
      - internal   # Can also reach the database

  database:
    image: postgres:latest
    networks:
      - internal   # Not exposed on the shared network

networks:
  shared:
    name: inter-project
    external: true
  internal: {}     # Project-specific, isolated
```

## Custom DNS with `extra_hosts`

You can add custom hostname-to-IP mappings to a container's `/etc/hosts` file using [`extra_hosts`](/reference/compose-file/services.md#extra_hosts). This is useful when a service needs to resolve a hostname that isn't registered in Docker's internal DNS. For example, a fixed-IP dependency or a staging endpoint:

```yaml
services:
  app:
    image: myapp
    extra_hosts:
      - "api.staging:192.168.1.100"
      - "cache.internal:192.168.1.101"
```

To map a hostname dynamically to the host machine's IP, use the special `host-gateway` value:

```yaml
services:
  app:
    image: myapp
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

On Linux, `host-gateway` resolves to the host's IP on the default bridge network. On Mac and Windows, Docker automatically provides this, `host-gateway` resolves to the same internal IP address as `host.docker.internal`.

You can also drive `extra_hosts` from environment variables, which makes it easy to point services at different targets per environment:

```yaml
services:
  app:
    image: myapp
    extra_hosts:
      - "api.service:${API_HOST:-127.0.0.1}"
      - "auth.service:${AUTH_HOST:-127.0.0.1}"
```

Where `.env.development` might set `API_HOST=localhost` and a production env file might set `API_HOST=10.0.1.50`.

To verify what has been injected, inspect the hosts file inside the container:

```bash
$ docker compose exec app cat /etc/hosts
```

## Multi-host networking

When deploying a Compose application on a Docker Engine with [Swarm mode enabled](/manuals/engine/swarm/_index.md), you can use the built-in `overlay` driver to enable multi-host communication. Overlay networks are always created as `attachable`. You can optionally set the [`attachable`](/reference/compose-file/networks.md#attachable) property to `false`.

To learn more, see the [overlay network driver documentation](/manuals/engine/network/drivers/overlay.md).

## Link containers

Links allow you to define extra aliases by which a service is reachable from another service. They are not required for basic service-to-service communication. By default, any service can reach any other service at that service's name. In the following example, `db` is reachable from `web` at both the hostnames `db` and `database`:

```yaml
services:
  web:
    build: .
    links:
      - "db:database"
  db:
    image: postgres:latest
```

See the [links reference](/reference/compose-file/services.md#links) for more information.

## Debugging

When a service can't reach another, work through the following steps in order: first confirm the network configuration looks right, then confirm the containers are actually attached, then test live connectivity.

### Inspect port mappings

To find out which host port maps to a container port, use `docker compose port`:

```bash
# Which host port maps to container port 5432 on db?
$ docker compose port db 5432
# Output: 0.0.0.0:8001
```

This is especially useful when using dynamic port mapping, where the host port changes on every `docker compose up`:

```yaml
services:
  web:
    image: nginx
    ports:
      - "80"   # Docker assigns the host port dynamically
```

```bash
$ docker compose port web 80
# Output: 0.0.0.0:55432
```

When you scale a service, each replica gets its own dynamic port. Use `--index` to query a specific replica:

```bash
$ docker compose up -d --scale web=3

$ docker compose port --index=1 web 80   # Output: 0.0.0.0:55001
$ docker compose port --index=2 web 80   # Output: 0.0.0.0:55002
$ docker compose port --index=3 web 80   # Output: 0.0.0.0:55003
```

By default, `docker compose port` looks for TCP mappings. If a service exposes both TCP and UDP on the same port, use `--protocol`:

```bash
$ docker compose port --protocol=udp myservice 53
```

### Verify network membership

To check which containers are attached to a network (useful when troubleshooting connectivity across external or custom networks):

```bash
$ docker network inspect <network-name>
```

### Check connectivity

If the network membership looks correct but services still can't reach each other, test connectivity from inside a running container using `docker compose exec`.

## Further reference information

For full details of the network configuration options available, see the following references:

- [Top-level `networks` element](/reference/compose-file/networks.md)
- [Service-level `networks` attribute](/reference/compose-file/services.md#networks)


---
## File: oci-artifact.md

---
title: Package and deploy Docker Compose applications as OCI artifacts
linkTitle: OCI artifact applications
weight: 110
description: Learn how to package, publish, and securely run Docker Compose applications from OCI-compliant registries.
keywords: cli, compose, oci, docker hub, artificats, publish, package, distribute, docker compose oci support
---

{{< summary-bar feature_name="Compose OCI artifact" >}}

Docker Compose supports working with [OCI artifacts](/manuals/docker-hub/repos/manage/hub-images/oci-artifacts.md), allowing you to package and distribute your Compose applications through container registries. This means you can store your Compose files alongside your container images, making it easier to version, share, and deploy your multi-container applications.

## Publish your Compose application as an OCI artifact

To distribute your Compose application as an OCI artifact, you can use the `docker compose publish` command, to publish it to an OCI-compliant registry. 
This allows others to then deploy your application directly from the registry.

The publish function supports most of the composition capabilities of Compose, like overrides, extends or include, [with some limitations](#limitations).

### General steps

1. Navigate to your Compose application's directory.  
   Ensure you're in the directory containing your `compose.yml` file or that you are specifying your Compose file with the `-f` flag.

2. In your terminal, sign in to your Docker account so you're authenticated with Docker Hub.

   ```console
   $ docker login
   ```

3. Use the `docker compose publish` command to push your application as an OCI artifact:

   ```console
   $ docker compose publish username/my-compose-app:latest
   ```
   If you have multiple Compose files, run:

   ```console
   $ docker compose -f compose-base.yml -f compose-production.yml publish username/my-compose-app:latest
   ```

### Advanced publishing options

When publishing, you can pass additional options: 
- `--oci-version`: Specify the OCI version (default is automatically determined).
- `--resolve-image-digests`: Pin image tags to digests.
- `--with-env`: Include environment variables in the published OCI artifact.

Compose checks to make sure there isn't any sensitive data in your configuration and displays your environment variables to confirm you want to publish them.

```text
...
you are about to publish sensitive data within your OCI artifact.
please double check that you are not leaking sensitive data
AWS Client ID
"services.serviceA.environment.AWS_ACCESS_KEY_ID": xxxxxxxxxx
AWS Secret Key
"services.serviceA.environment.AWS_SECRET_ACCESS_KEY": aws"xxxx/xxxx+xxxx+"
Github authentication
"GITHUB_TOKEN": ghp_xxxxxxxxxx
JSON Web Token
"": xxxxxxx.xxxxxxxx.xxxxxxxx
Private Key
"": -----BEGIN DSA PRIVATE KEY-----
xxxxx
-----END DSA PRIVATE KEY-----
Are you ok to publish these sensitive data? [y/N]:y

you are about to publish environment variables within your OCI artifact.
please double check that you are not leaking sensitive data
Service/Config  serviceA
FOO=bar
Service/Config  serviceB
FOO=bar
QUIX=
BAR=baz
Are you ok to publish these environment variables? [y/N]: 
```

If you decline, the publish process stops without sending anything to the registry.

## Limitations

There are limitations to publishing Compose applications as OCI artifacts. You can't publish a Compose configuration:
- With service(s) containing bind mounts
- With service(s) containing only a `build` section
- That includes local files with the `include` attribute. To publish successfully, ensure that any included local files are also published. You can then use  `include` to reference these files as remote `include` is supported.

## Start an OCI artifact application

To start a Docker Compose application that uses an OCI artifact, you can use the `-f` (or `--file`) flag followed by the OCI artifact reference. This allows you to specify a Compose file stored as an OCI artifact in a registry.

The `oci://` prefix indicates that the Compose file should be pulled from an OCI-compliant registry rather than loaded from the local filesystem.

```console
$ docker compose -f oci://docker.io/username/my-compose-app:latest up
```

To then run the Compose application, use the `docker compose up` command with the `-f` flag pointing to your OCI artifact:

```console
$ docker compose -f oci://docker.io/username/my-compose-app:latest up
```

### Troubleshooting

When you run an application from an OCI artifact, Compose may display warning messages that require you to confirm the following so as to limit the risk of running a malicious application:

- A list of the interpolation variables used along with their values
- A list of all environment variables used by the application
- If your OCI artifact application is using another remote resources, for example via [`include`](/reference/compose-file/include/).

```text 
$ REGISTRY=myregistry.com docker compose -f oci://docker.io/username/my-compose-app:latest up

Found the following variables in configuration:
VARIABLE     VALUE                SOURCE        REQUIRED    DEFAULT
REGISTRY     myregistry.com      command-line   yes         
TAG          v1.0                environment    no          latest
DOCKERFILE   Dockerfile          default        no          Dockerfile
API_KEY      <unset>             none           no          

Do you want to proceed with these variables? [Y/n]:y

Warning: This Compose project includes files from remote sources:
- oci://registry.example.com/stack:latest
Remote includes could potentially be malicious. Make sure you trust the source.
Do you want to continue? [y/N]: 
```

If you agree to start the application, Compose displays the directory where all the resources from the OCI artifact have been downloaded:

```text
...
Do you want to continue? [y/N]: y

Your compose stack "oci://registry.example.com/stack:latest" is stored in "~/Library/Caches/docker-compose/964e715660d6f6c3b384e05e7338613795f7dcd3613890cfa57e3540353b9d6d"
```

The `docker compose publish` command supports non-interactive execution, letting you skip the confirmation prompt by including the `-y` (or `--yes`) flag: 

```console
$ docker compose publish -y username/my-compose-app:latest
```

## Next steps

- [Familiarize yourself with Compose's trust model](/manuals/compose/trust-model.md)
- [Learn about OCI artifacts in Docker Hub](/manuals/docker-hub/repos/manage/hub-images/oci-artifacts.md)
- [Compose publish command](/reference/cli/docker/compose/publish/)
- [Understand `include`](/reference/compose-file/include.md)


---
## File: production.md

---
description: Learn how to configure, deploy, and update Docker Compose applications for production environments.
keywords: compose, orchestration, containers, production, production docker compose configuration
title: Use Compose in production
weight: 100
aliases:
- /compose/production/
---

When you define your app with Compose in development, you can use this
definition to run your application in different environments such as CI,
staging, and production.

The easiest way to deploy an application is to run it on a single server,
similar to how you would run your development environment. If you want to scale
up your application, you can run Compose apps on a Swarm cluster.

### Modify your Compose file for production

You may need to make changes to your app configuration to make it ready for
production. These changes might include:

- Removing any volume bindings for application code, so that code stays inside
  the container and can't be changed from outside
- Binding to different ports on the host
- Setting environment variables differently, such as reducing the verbosity of
  logging, or to specify settings for external services such as an email server
- Specifying a restart policy like [`restart: always`](/reference/compose-file/services.md#restart)to avoid downtime
- Adding extra services such as a log aggregator

For this reason, consider defining an additional Compose file, for example
`compose.production.yaml`, with production-specific
configuration details. This configuration file only needs to include the changes you want to make from the original Compose file. The additional Compose file
is then applied over the original `compose.yaml` to create a new configuration.

Once you have a second configuration file, you can use it with the
`-f` option:

```console
$ docker compose -f compose.yaml -f compose.production.yaml up -d
```

See [Using multiple compose files](multiple-compose-files/_index.md) for a more complete example, and other options.

### Deploying changes

When you make changes to your app code, remember to rebuild your image and
recreate your app's containers. To redeploy a service called
`web`, use:

```console
$ docker compose build web
$ docker compose up --no-deps -d web
```

This first command rebuilds the image for `web` and then stops, destroys, and recreates
just the `web` service. The `--no-deps` flag prevents Compose from also
recreating any services that `web` depends on.

### Running Compose on a single server

You can use Compose to deploy an app to a remote Docker host by setting the
`DOCKER_HOST`, `DOCKER_TLS_VERIFY`, and `DOCKER_CERT_PATH` environment variables
appropriately. For more information, see [pre-defined environment variables](environment-variables/envvars.md).

Once you've set up your environment variables, all the normal `docker compose`
commands work with no further configuration.

## Next steps

- [Familiarize yourself with Compose's trust model](/manuals/compose/trust-model.md)
- [Using multiple Compose files](multiple-compose-files/_index.md)



---
## File: profiles.md

---
title: Using profiles with Compose
linkTitle: Use service profiles
weight: 20
description: How to use profiles with Docker Compose
keywords: cli, compose, profile, profiles reference
aliases:
- /compose/profiles/
---

{{% include "compose/profiles.md" %}}

## Assigning profiles to services

Services are associated with profiles through the
[`profiles` attribute](/reference/compose-file/services.md#profiles) which takes an
array of profile names:

```yaml
services:
  frontend:
    image: frontend
    profiles: [frontend]

  phpmyadmin:
    image: phpmyadmin
    depends_on: [db]
    profiles: [debug]

  backend:
    image: backend

  db:
    image: mysql
```

Here the services `frontend` and `phpmyadmin` are assigned to the profiles
`frontend` and `debug` respectively and as such are only started when their
respective profiles are enabled.

Services without a `profiles` attribute are always enabled. In this
case running `docker compose up` would only start `backend` and `db`.

Valid profiles names follow the regex format of `[a-zA-Z0-9][a-zA-Z0-9_.-]+`.

> [!TIP]
>
> The core services of your application shouldn't be assigned `profiles` so
> they are always enabled and automatically started.

## Start specific profiles

To start a specific profile supply the `--profile` [command-line option](/reference/cli/docker/compose/) or
use the [`COMPOSE_PROFILES` environment variable](environment-variables/envvars.md#compose_profiles):

```console
$ docker compose --profile debug up
```
```console
$ COMPOSE_PROFILES=debug docker compose up
```

Both commands start the services with the `debug` profile enabled.
In the previous `compose.yaml` file, this starts the services
`db`, `backend` and `phpmyadmin`.

### Start multiple profiles

You can also enable
multiple profiles, e.g. with `docker compose --profile frontend --profile debug up`
the profiles `frontend` and `debug` will be enabled.

Multiple profiles can be specified by passing multiple `--profile` flags or
a comma-separated list for the `COMPOSE_PROFILES` environment variable:

```console
$ docker compose --profile frontend --profile debug up
```

```console
$ COMPOSE_PROFILES=frontend,debug docker compose up
```

If you want to enable all profiles at the same time, you can run `docker compose --profile "*"`.

## Auto-starting profiles and dependency resolution

When you explicitly target a service on the command line that has one or more profiles assigned, you do not need to enable the profile manually as Compose runs that service regardless of whether its profile is activated. This is useful for running one-off services or debugging tools.

Only the targeted service (and any of its declared dependencies via `depends_on`) is started. Other services that share the same profile will not be started unless:
- They are also explicitly targeted, or
- The profile is explicitly enabled using `--profile` or `COMPOSE_PROFILES`.

When a service with assigned `profiles` is explicitly targeted on the command
line its profiles are started automatically so you don't need to start them
manually. This can be used for one-off services and debugging tools.
As an example consider the following configuration:

```yaml
services:
  backend:
    image: backend

  db:
    image: mysql

  db-migrations:
    image: backend
    command: myapp migrate
    depends_on:
      - db
    profiles:
      - tools
```

```sh
# Only start backend and db (no profiles involved)
$ docker compose up -d

# Run the db-migrations service without manually enabling the 'tools' profile
$ docker compose run db-migrations
```

In this example, `db-migrations` runs even though it is assigned to the tools profile, because it was explicitly targeted. The `db` service is also started automatically because it is listed in `depends_on`.

If the targeted service has dependencies that are also gated behind a profile, you must ensure those dependencies are either: 
 - In the same profile
 - Started separately
 - Not assigned to any profile so are always enabled

## Stop application and services with specific profiles

As with starting specific profiles, you can use the `--profile` [command-line option](/reference/cli/docker/compose/#use--p-to-specify-a-project-name) or
use the [`COMPOSE_PROFILES` environment variable](environment-variables/envvars.md#compose_profiles):

```console
$ docker compose --profile debug down
```
```console
$ COMPOSE_PROFILES=debug docker compose down
```

Both commands stop and remove services with the `debug` profile and services without a profile. In the following `compose.yaml` file, this stops the services `db`, `backend` and `phpmyadmin`.

```yaml
services:
  frontend:
    image: frontend
    profiles: [frontend]

  phpmyadmin:
    image: phpmyadmin
    depends_on: [db]
    profiles: [debug]

  backend:
    image: backend

  db:
    image: mysql
```

if you only want to stop the `phpmyadmin` service, you can run 

```console 
$ docker compose down phpmyadmin
``` 
or 
```console 
$ docker compose stop phpmyadmin
```

> [!NOTE]
>
> Running `docker compose down` only stops `backend` and `db`.

## Reference information

[`profiles`](/reference/compose-file/services.md#profiles)


---
## File: project-name.md

---
title: Specify a project name
weight: 10
description: Learn how to set a custom project name in Compose and understand the precedence of each method.
keywords: name, compose, project, -p flag, name top-level element
aliases:
- /compose/project-name/
---

By default, Compose assigns the project name based on the name of the directory that contains the Compose file. You can override this with several methods.

This page offers examples of scenarios where custom project names can be helpful, outlines the various methods to set a project name, and provides the order of precedence for each approach.

> [!NOTE]
>
> The default project directory is the base directory of the Compose file. A custom value can also be set
> for it using the [`--project-directory` command line option](/reference/cli/docker/compose/#options).

## Example use cases

Compose uses a project name to isolate environments from each other. There are multiple contexts where a project name is useful:

- On a development host: Create multiple copies of a single environment, useful for running stable copies for each feature branch of a project.
- On a CI server: Prevent interference between builds by setting the project name to a unique build number.
- On a shared or development host: Avoid interference between different projects that might share the same service names.

## Set a project name

Project names must contain only lowercase letters, decimal digits, dashes, and
underscores, and must begin with a lowercase letter or decimal digit. If the
base name of the project directory or current directory violates this
constraint, alternative mechanisms are available.

The precedence order for each method, from highest to lowest, is as follows:

1. The `-p` command line flag. 
2. The [COMPOSE_PROJECT_NAME environment variable](environment-variables/envvars.md).
3. The [top-level `name:` attribute](/reference/compose-file/version-and-name.md) in your Compose file. Or the last `name:` if you [specify multiple Compose files](multiple-compose-files/merge.md) in the command line with the `-f` flag.
4. The base name of the project directory containing your Compose file. Or the base name of the first Compose file if you [specify multiple Compose files](multiple-compose-files/merge.md) in the command line with the `-f` flag. 
5. The base name of the current directory if no Compose file is specified.

## What's next?

- Read up on [working with multiple Compose files](multiple-compose-files/_index.md).
- Explore some [sample apps](https://github.com/docker/awesome-compose).


---
## File: provider-services.md

---
title: Use provider services
description: Learn how to use provider services in Docker Compose to integrate external capabilities into your applications
keywords: compose, docker compose, provider, services, platform capabilities, integration, model runner, ai
weight: 130
---

{{< summary-bar feature_name="Compose provider services" >}}

Docker Compose supports provider services, which allow integration with services whose lifecycles are managed by third-party components rather than by Compose itself.  
This feature enables you to define and utilize platform-specific services without the need for manual setup or direct lifecycle management.

## What are provider services?

Provider services are a special type of service in Compose that represents platform capabilities rather than containers.
They allow you to declare dependencies on specific platform features that your application needs.

When you define a provider service in your Compose file, Compose works with the platform to provision and configure
the requested capability, making it available to your application services.

## Using provider services

To use a provider service in your Compose file, you need to:

1. Define a service with the `provider` attribute
2. Specify the `type` of provider you want to use
3. Configure any provider-specific options
4. Declare dependencies from your application services to the provider service

Here's a basic example:

```yaml
services:
  database:
    provider:
      type: awesomecloud
      options:
        type: mysql
        foo: bar  
  app:
    image: myapp 
    depends_on:
       - database
```

Notice the dedicated `provider` attribute in the `database` service.
This attribute specifies that the service is managed by a provider and lets you define options specific to that provider type.

The `depends_on` attribute in the `app` service specifies that it depends on the `database` service.
This means that the `database` service will be started before the `app` service, allowing the provider information
to be injected into the `app` service.

## How it works

During the `docker compose up` command execution, Compose identifies services relying on providers and works with them to provision
the requested capabilities. The provider then populates Compose model with information about how to access the provisioned resource.

This information is passed to services that declare a dependency on the provider service, typically through environment
variables. The naming convention for these variables is:

```env
<<PROVIDER_SERVICE_NAME>>_<<VARIABLE_NAME>>
```

For example, if your provider service is named `database`, your application service might receive environment variables like:

- `DATABASE_URL` with the URL to access the provisioned resource
- `DATABASE_TOKEN` with an authentication token
- Other provider-specific variables

Your application can then use these environment variables to interact with the provisioned resource.

## Provider types

The `type` field in a provider service references the name of either:

1. A Docker CLI plugin (e.g., `docker-model`)
2. A binary available in the user's PATH
3. A path to the binary or script to execute

When Compose encounters a provider service, it looks for a plugin or binary with the specified name to handle the provisioning of the requested capability.

For example, if you specify `type: model`, Compose will look for a Docker CLI plugin named `docker-model` or a binary named `model` in the PATH.

```yaml
services:
  ai-runner:
    provider:
      type: model  # Looks for docker-model plugin or model binary
      options:
        model: ai/example-model
```

The plugin or binary is responsible for:

1. Interpreting the options provided in the provider service
2. Provisioning the requested capability
3. Returning information about how to access the provisioned resource

This information is then passed to dependent services as environment variables.

> [!TIP]
>
> If you're working with AI models in Compose, use the [`models` top-level element](/manuals/ai/compose/models-and-compose.md) instead.

## Benefits of using provider services

Using provider services in your Compose applications offers several benefits:

1. Simplified configuration: You don't need to manually configure and manage platform capabilities
2. Declarative approach: You can declare all your application's dependencies in one place
3. Consistent workflow: You use the same Compose commands to manage your entire application, including platform capabilities

## Creating your own provider

If you want to create your own provider to extend Compose with custom capabilities, you can implement a Compose plugin that registers provider types.

For detailed information on how to create and implement your own provider, refer to the [Compose Extensions documentation](https://github.com/docker/compose/blob/main/docs/extension.md).   
This guide explains the extension mechanism that allows you to add new provider types to Compose.

## Reference

- [Docker Model Runner documentation](/manuals/ai/model-runner.md)
- [Compose Extensions documentation](https://github.com/docker/compose/blob/main/docs/extension.md)

---
## File: startup-order.md

---
description: Learn how to manage service startup and shutdown order in Docker Compose using depends_on and healthchecks.
keywords: docker compose startup order, compose shutdown order, depends_on, service healthcheck, control service dependencies
title: Control startup and shutdown order in Compose
linkTitle: Control startup order
weight: 30
aliases:
- /compose/startup-order/
---

You can control the order of service startup and shutdown with the
[depends_on](/reference/compose-file/services.md#depends_on) attribute. Compose always starts and stops
containers in dependency order, where dependencies are determined by
`depends_on`, `links`, `volumes_from`, and `network_mode: "service:..."`.

For example, if your application needs to access a database and both services are started with `docker compose up`, there is a chance this will fail since the application service might start before the database service and won't find a database able to handle its SQL statements. 

## Control startup

On startup, Compose does not wait until a container is "ready", only until it's running. This can cause issues if, for example, you have a relational database system that needs to start its own services before being able to handle incoming connections.

The solution for detecting the ready state of a service is  to use the `condition` attribute with one of the following options:

- `service_started`
- `service_healthy`. This specifies that a dependency is expected to be “healthy”, which is defined with `healthcheck`, before starting a dependent service.
- `service_completed_successfully`. This specifies that a dependency is expected to run to successful completion before starting a dependent service.

## Example

```yaml
services:
  web:
    build: .
    depends_on:
      db:
        condition: service_healthy
        restart: true
      redis:
        condition: service_started
  redis:
    image: redis
  db:
    image: postgres:18
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 10s
      retries: 5
      start_period: 30s
      timeout: 10s
```

Compose creates services in dependency order. `db` and `redis` are created before `web`. 

Compose waits for healthchecks to pass on dependencies marked with `service_healthy`. `db` is expected to be "healthy" (as indicated by `healthcheck`) before `web` is created.

`restart: true` ensures that if `db` is updated or restarted due to an explicit Compose operation, for example `docker compose restart`, the `web` service is also restarted automatically, ensuring it re-establishes connections or dependencies correctly.

The healthcheck for the `db` service uses the `pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}` command to check if the PostgreSQL database is ready. The service is retried every 10 seconds, up to 5 times.

Compose also removes services in dependency order. `web` is removed before `db` and `redis`.

## Reference information 

- [`depends_on`](/reference/compose-file/services.md#depends_on)
- [`healthcheck`](/reference/compose-file/services.md#healthcheck)


---
## File: use-secrets.md

---
title: Manage secrets securely in Docker Compose
linkTitle: Secrets in Compose
weight: 60
description: Learn how to securely manage runtime and build-time secrets in Docker Compose.
keywords: secrets, compose, security, environment variables, docker secrets, secure Docker builds, sensitive data in containers
tags: [Secrets]
aliases:
- /compose/use-secrets/
---

A secret is any piece of data, such as a password, certificate, or API key, that shouldn’t be transmitted over a network or stored unencrypted in a Dockerfile or in your application’s source code.

{{% include "compose/secrets.md" %}}

Environment variables are often available to all processes, and it can be difficult to track access. They can also be printed in logs when debugging errors without your knowledge. Using secrets mitigates these risks.

## Use secrets

Secrets are mounted as a file in `/run/secrets/<secret_name>` inside the container.

> [!NOTE]
>
> Secrets are supported on Linux containers only. Compose delivers each secret by bind-mounting a single file into the container, and Windows containers support bind-mounting directories only.

Getting a secret into a container is a two-step process. First, define the secret using the [top-level secrets element in your Compose file](/reference/compose-file/secrets.md). Next, update your service definitions to reference the secrets they require with the [secrets attribute](/reference/compose-file/services.md#secrets). Compose grants access to secrets on a per-service basis.

Unlike the other methods, this permits granular access control within a service container via standard filesystem permissions.

## Examples

### Single-service secret injection

In the following example, the frontend service is given access to the `my_secret` secret. In the container, `/run/secrets/my_secret` is set to the contents of the file `./my_secret.txt`.

```yaml
services:
  myapp:
    image: myapp:latest
    secrets:
      - my_secret
secrets:
  my_secret:
    file: ./my_secret.txt
```

### Multi-service secret sharing and password management

```yaml
services:
   db:
     image: mysql:latest
     volumes:
       - db_data:/var/lib/mysql
     environment:
       MYSQL_ROOT_PASSWORD_FILE: /run/secrets/db_root_password
       MYSQL_DATABASE: wordpress
       MYSQL_USER: wordpress
       MYSQL_PASSWORD_FILE: /run/secrets/db_password
     secrets:
       - db_root_password
       - db_password

   wordpress:
     depends_on:
       - db
     image: wordpress:latest
     ports:
       - "8000:80"
     environment:
       WORDPRESS_DB_HOST: db:3306
       WORDPRESS_DB_USER: wordpress
       WORDPRESS_DB_PASSWORD_FILE: /run/secrets/db_password
     secrets:
       - db_password


secrets:
   db_password:
     file: db_password.txt
   db_root_password:
     file: db_root_password.txt

volumes:
    db_data:
```
In the advanced example above:

- The `secrets` attribute under each service defines the secrets you want to inject into the specific container.
- The top-level `secrets` section defines the variables `db_password` and `db_root_password` and provides the `file` that populates their values.
- The deployment of each container means Docker creates a bind mount under `/run/secrets/<secret_name>` with their specific values.

> [!NOTE]
>
> The `_FILE` environment variables demonstrated here are a convention used by some images, including Docker Official Images like [mysql](https://hub.docker.com/_/mysql) and [postgres](https://hub.docker.com/_/postgres).

### Build secrets

In the following example, the `npm_token` secret is made available at build time. Its value is taken from the `NPM_TOKEN` environment variable.

```yaml
services:
  myapp:
    build:
      secrets:
        - npm_token
      context: .

secrets:
  npm_token:
    environment: NPM_TOKEN
```

## Resources

- [Familiarize yourself with Compose's trust model](/manuals/compose/trust-model.md)
- [Secrets top-level element](/reference/compose-file/secrets.md)
- [Secrets attribute for services top-level element](/reference/compose-file/services.md#secrets)
- [Build secrets](https://docs.docker.com/build/building/secrets/)


---
## File: _index.md

---
title: Docker Compose
weight: 30
description: Learn how to use Docker Compose to define and run multi-container applications
  with this detailed introduction to the tool.
keywords: docker compose, docker-compose, compose.yaml, docker compose command, multi-container applications, container orchestration, docker cli
params:
  sidebar:
    group: Application development
grid:
- title: Why use Compose?
  description: Understand Docker Compose's key benefits
  icon: magnifying-glass
  link: /compose/intro/features-uses/
- title: How Compose works 
  description: Understand how Compose works
  icon: squares-2x2
  link: /compose/intro/compose-application-model/
- title: Install Compose
  description: Follow the instructions on how to install Docker Compose.
  icon: arrow-down-tray
  link: /compose/install
- title: Quickstart
  description: Learn the key concepts of Docker Compose whilst building a simple Python
    web application.
  icon: magnifying-glass-plus
  link: /compose/gettingstarted
- title: View the release notes
  description: Find out about the latest enhancements and bug fixes.
  icon: document-plus
  link: "https://github.com/docker/compose/releases"
- title: Explore the Compose file reference
  description: Find information on defining services, networks, and volumes for a
    Docker application.
  icon: arrows-right-left
  link: /reference/compose-file
- title: Use Compose Bridge
  description: Transform your Compose configuration file into configuration files for different platforms, such as Kubernetes.
  icon: arrow-down
  link: /compose/bridge
- title: Browse common FAQs
  description: Explore general FAQs and find out how to give feedback.
  icon: question-mark-circle
  link: /compose/faq
aliases:
- /compose/overview/
- /compose/swarm/
- /compose/releases/migrate/
---

Docker Compose is a tool for defining and running multi-container applications. 
It is the key to unlocking a streamlined and efficient development and deployment experience. 

Compose simplifies the control of your entire application stack, making it easy to manage services, networks, and volumes in a single YAML configuration file. Then, with a single command, you create and start all the services
from your configuration file.

Compose works in all environments - production, staging, development, testing, as
well as CI workflows. It also has commands for managing the whole lifecycle of your application:

 - Start, stop, and rebuild services
 - View the status of running services
 - Stream the log output of running services
 - Run a one-off command on a service

{{< grid >}}


---
## File: _index.md

---
description: Learn how to install Docker Compose. Compose is available natively on
  Docker Desktop, as a Docker Engine plugin, and as a standalone tool.
keywords: install docker compose, docker compose plugin, install compose linux, install docker desktop, docker compose windows, standalone docker compose, docker compose not found
title: Overview of installing Docker Compose
linkTitle: Install
weight: 20
toc_max: 3
---

This page summarizes the different ways you can install Docker Compose, depending on your platform and needs.

## Installation scenarios 

### Docker Desktop (Recommended)

The easiest and recommended way to get Docker Compose is to install Docker Desktop. 

Docker Desktop includes Docker Compose along with Docker Engine and Docker CLI which are Compose prerequisites. 

Docker Desktop is available for:
- [Linux](/manuals/desktop/setup/install/linux/_index.md)
- [Mac](/manuals/desktop/setup/install/mac-install.md)
- [Windows](/manuals/desktop/setup/install/windows-install.md)

> [!TIP]
> 
> If you have already installed Docker Desktop, you can check which version of Compose you have by selecting **About Docker Desktop** from the Docker menu {{< inline-image src="../../desktop/images/whale-x.svg" alt="whale menu" >}}.

### Plugin (Linux only)

> [!IMPORTANT]
>
> This method is only available on Linux.

If you already have Docker Engine and Docker CLI installed, you can install the Docker Compose plugin from the command line, by either:
- [Using Docker's repository](linux.md#install-using-the-repository)
- [Downloading and installing manually](linux.md#install-the-plugin-manually)

### Standalone (Legacy)

> [!WARNING]
>
> This install scenario is not recommended and is only supported for backward compatibility purposes.

You can [install the Docker Compose standalone](standalone.md) on Linux or on Windows Server.



---
## File: linux.md

---
description: Step-by-step instructions for installing the Docker Compose plugin on Linux using a package repository or manual method.
keywords: install docker compose linux, docker compose plugin, docker-compose-plugin linux, docker compose v2, docker compose manual install, linux docker compose
toc_max: 3
title: Install the Docker Compose plugin
linkTitle: Plugin
aliases:
- /compose/install/compose-plugin/
weight: 10
---

This page contains instructions on how to install the Docker Compose plugin on Linux from the command line.

To install the Docker Compose plugin on Linux, you can either:
- [Set up Docker's repository on your Linux system](#install-using-the-repository).
- [Install manually](#install-the-plugin-manually).

> [!NOTE]
>
> These instructions assume you already have Docker Engine and Docker CLI installed and now want to install the Docker Compose plugin. 

## Install using the repository

1. Set up the repository. Find distribution-specific instructions in:

    [Ubuntu](/manuals/engine/install/ubuntu.md#install-using-the-repository) |
    [CentOS](/manuals/engine/install/centos.md#set-up-the-repository) |
    [Debian](/manuals/engine/install/debian.md#install-using-the-repository) |
    [Raspberry Pi OS](/manuals/engine/install/raspberry-pi-os.md#install-using-the-repository) |
    [Fedora](/manuals/engine/install/fedora.md#set-up-the-repository) |
    [RHEL](/manuals/engine/install/rhel.md#set-up-the-repository).

2. Update the package index, and install the latest version of Docker Compose:

    * For Ubuntu and Debian, run:

        ```console
        $ sudo apt-get update
        $ sudo apt-get install docker-compose-plugin
        ```
    * For RPM-based distributions, run:

        ```console
        $ sudo yum update
        $ sudo yum install docker-compose-plugin
        ```

3.  Verify that Docker Compose is installed correctly by checking the version.

    ```console
    $ docker compose version
    ```

### Update Docker Compose

To update the Docker Compose plugin, run the following commands:

* For Ubuntu and Debian, run:

    ```console
    $ sudo apt-get update
    $ sudo apt-get install docker-compose-plugin
    ```
* For RPM-based distributions, run:

    ```console
    $ sudo yum update
    $ sudo yum install docker-compose-plugin
    ```

## Install the plugin manually

> [!WARNING]
>
> Manual installations don’t auto-update. For ease of maintenance, use the Docker repository method.

1.  To download and install the Docker Compose CLI plugin, run:

    ```console
    $ DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
    $ mkdir -p $DOCKER_CONFIG/cli-plugins
    $ curl -SL https://github.com/docker/compose/releases/download/{{% param "compose_version" %}}/docker-compose-linux-x86_64 -o $DOCKER_CONFIG/cli-plugins/docker-compose
    ```

    This command downloads and installs the latest release of Docker Compose for the active user under `$HOME` directory.

    To install:
    - Docker Compose for _all users_ on your system, replace `~/.docker/cli-plugins` with `/usr/local/lib/docker/cli-plugins`.
    - A different version of Compose, substitute `{{% param "compose_version" %}}` with the version of Compose you want to use.
    - For a different architecture, substitute `x86_64` with the [architecture you want](https://github.com/docker/compose/releases).   


2. Apply executable permissions to the binary:

    ```console
    $ chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose
    ```
    or, if you chose to install Compose for all users:

    ```console
    $ sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
    ```

3. Test the installation.

    ```console
    $ docker compose version
    ```

## What's next?

- [Understand how Compose works](/manuals/compose/intro/compose-application-model.md)
- [Try the Quickstart guide](/manuals/compose/gettingstarted.md)


---
## File: standalone.md

---
title: Install the Docker Compose standalone (Legacy)
linkTitle: Standalone (Legacy)
description: Instructions for installing the legacy Docker Compose standalone tool on Linux and Windows Server
keywords: install docker-compose, standalone docker compose, docker-compose windows server, install docker compose linux, legacy compose install
toc_max: 3
weight: 20
---

> [!WARNING]
>
> This install scenario is not recommended and is only supported for backward compatibility purposes.
> Use [Docker Desktop](/manuals/desktop/_index.md) or the
> [Docker Compose plugin](/manuals/compose/install/linux.md) instead.
> Use the standalone binary only if you cannot use either of these options.

This page contains instructions on how to install Docker Compose standalone on Linux or Windows Server, from the command line.

> [!WARNING]
>
> The Docker Compose standalone uses the `-compose` syntax instead of the current standard syntax `compose`.  
> For example, you must type `docker-compose up` when using Docker Compose standalone, instead of `docker compose up`.
> Use it only for backward compatibility.

## On Linux

1. To download and install the Docker Compose standalone, run:

   ```console
   $ curl -SL https://github.com/docker/compose/releases/download/{{% param "compose_version" %}}/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose
   ```

2. Apply executable permissions to the standalone binary in the target path for the installation.

   ```console
   $ chmod +x /usr/local/bin/docker-compose
   ```

3. Test and execute Docker Compose commands using `docker-compose`.

> [!TIP]
>
> If the command `docker-compose` fails after installation, check your path.
> You can also create a symbolic link to `/usr/bin` or any other directory in your path.
> For example:
>
> ```console
> $ sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
> ```

## On Windows Server

Follow these instructions if you are [running the Docker daemon directly
on Microsoft Windows Server](/manuals/engine/install/binaries.md#install-server-and-client-binaries-on-windows) and want to install Docker Compose.

1.  Run PowerShell as an administrator.
    In order to proceed with the installation, select **Yes** when asked if you want this app to make changes to your device.

2.  Optional. Ensure TLS1.2 is enabled.
    GitHub requires TLS1.2 for secure connections. If you’re using an older version of Windows Server, for example 2016, or suspect that TLS1.2 is not enabled, run the following command in PowerShell:

    ```powershell
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    ```

3.  Download the latest release of Docker Compose ({{% param "compose_version" %}}). Run the following command:

    ```powershell
     Start-BitsTransfer -Source "https://github.com/docker/compose/releases/download/{{% param "compose_version" %}}/docker-compose-windows-x86_64.exe" -Destination $Env:ProgramFiles\Docker\docker-compose.exe
    ```

    To install a different version of Docker Compose, substitute `{{% param "compose_version" %}}` with the version of Compose you want to use.

    > [!NOTE]
    >
    > On Windows Server 2019 you can add the Compose executable to `$Env:ProgramFiles\Docker`.
    > Because this directory is registered in the system `PATH`, you can run the `docker-compose --version`
    > command on the subsequent step with no additional configuration.

4.  Test the installation.

    ```console
    $ docker-compose.exe version
    Docker Compose version {{% param "compose_version" %}}
    ```

## What's next?

- [Understand how Compose works](/manuals/compose/intro/compose-application-model.md)
- [Try the Quickstart guide](/manuals/compose/gettingstarted.md)


---
## File: uninstall.md

---
description: How to uninstall Docker Compose
keywords: compose, orchestration, uninstall, uninstallation, docker, documentation
title: Uninstall Docker Compose
linkTitle: Uninstall 
---

How you uninstall Docker Compose depends on how it was installed. This guide covers uninstallation instructions for:

- Docker Compose installed via Docker Desktop
- Docker Compose installed as a CLI plugin

## Uninstalling Docker Compose with Docker Desktop

If you want to uninstall Docker Compose and you have installed Docker Desktop, see [Uninstall Docker Desktop](/manuals/desktop/uninstall.md).

> [!WARNING]
>
> Unless you have other Docker instances installed on that specific environment, uninstalling Docker Desktop removes all Docker components, including Docker Engine, Docker CLI, and Docker Compose.

## Uninstalling the Docker Compose CLI plugin

If you installed Docker Compose via a package manager, run:

On Ubuntu or Debian:

   ```console
   $ sudo apt-get remove docker-compose-plugin
   ```
On RPM-based distributions:

   ```console
   $ sudo yum remove docker-compose-plugin
   ```

### Manually installed

If you installed Docker Compose manually (using curl), remove it by deleting the binary:

   ```console
   $ rm $DOCKER_CONFIG/cli-plugins/docker-compose
   ```

### Remove for all users

If installed for all users, remove it from the system directory:

   ```console
   $ rm /usr/local/lib/docker/cli-plugins/docker-compose
   ```

> [!NOTE]
>
> If you get a **Permission denied** error using either of the previous
> methods, you do not have the permissions needed to remove
> Docker Compose. To force the removal, prepend `sudo` to either of the previous instructions and run it again.

### Inspect the location of the Compose CLI plugin

To check where Compose is installed, use:

```console
$ docker info --format '{{range .ClientInfo.Plugins}}{{if eq .Name "compose"}}{{.Path}}{{end}}{{end}}'
```


---
## File: compose-application-model.md

---
title: How Compose works
weight: 10
description: Learn how Docker Compose works, from the application model to Compose files and CLI, whilst following a detailed example.
keywords: docker compose, compose.yaml, docker compose model, compose cli, multi-container application, compose example 
aliases:
- /compose/compose-file/02-model/
- /compose/compose-application-model/
---

With Docker Compose you use a YAML configuration file, known as the [Compose file](#the-compose-file), to configure your application’s services, and then you create and start all the services from your configuration with the [Compose CLI](#cli). 

The Compose file, or `compose.yaml` file, follows the rules provided by the [Compose Specification](/reference/compose-file/_index.md) in how to define multi-container applications. This is the Docker Compose implementation of the formal [Compose Specification](https://github.com/compose-spec/compose-spec). 

{{< accordion title="The Compose application model" >}}

Computing components of an application are defined as [services](/reference/compose-file/services.md). A service is an abstract concept implemented on platforms by running the same container image, and configuration, one or more times.

Services communicate with each other through [networks](/reference/compose-file/networks.md). In the Compose Specification, a network is a platform capability abstraction to establish an IP route between containers within services connected together.

Services store and share persistent data into [volumes](/reference/compose-file/volumes.md). The Specification describes such a persistent data as a high-level filesystem mount with global options.

Some services require configuration data that is dependent on the runtime or platform. For this, the Specification defines a dedicated [configs](/reference/compose-file/configs.md) concept. From inside the container, configs behave like volumes—they’re mounted as files. However, configs are defined differently at the platform level.

A [secret](/reference/compose-file/secrets.md) is a specific flavor of configuration data for sensitive data that should not be exposed without security considerations. Secrets are made available to services as files mounted into their containers, but the platform-specific resources to provide sensitive data are specific enough to deserve a distinct concept and definition within the Compose Specification.

> [!NOTE]
>
> With volumes, configs and secrets you can have a simple declaration at the top-level and then add more platform-specific information at the service level.

A project is an individual deployment of an application specification on a platform. A project's name, set with the top-level [`name`](/reference/compose-file/version-and-name.md) attribute, is used to group
resources together and isolate them from other applications or other installation of the same Compose-specified application with distinct parameters. If you are creating resources on a platform, you must prefix resource names by project and
set the label `com.docker.compose.project`.

Compose offers a way for you to set a custom project name and override this name, so that the same `compose.yaml` file can be deployed twice on the same infrastructure, without changes, by just passing a distinct name.

{{< /accordion >}} 

## The Compose file

The default path for a Compose file is `compose.yaml` (preferred) or `compose.yml` that is placed in the working directory.
Compose also supports `docker-compose.yaml` and `docker-compose.yml` for backwards compatibility of earlier versions.
If both files exist, Compose prefers the canonical `compose.yaml`.

You can use [fragments](/reference/compose-file/fragments.md) and [extensions](/reference/compose-file/extension.md) to keep your Compose file efficient and easy to maintain.

Multiple Compose files can be [merged](/reference/compose-file/merge.md) together to define the application model. The combination of YAML files is implemented by appending or overriding YAML elements based on the Compose file order you set. 
Simple attributes and maps get overridden by the highest order Compose file, lists get merged by appending. Relative
paths are resolved based on the first Compose file's parent folder, whenever complementary files being
merged are hosted in other folders. As some Compose file elements can both be expressed as single strings or complex objects, merges apply to
the expanded form. For more information, see [Working with multiple Compose files](/manuals/compose/how-tos/multiple-compose-files/_index.md).

If you want to reuse other Compose files, or factor out parts of your application model into separate Compose files, you can also use [`include`](/reference/compose-file/include.md). This is useful if your Compose application is dependent on another application which is managed by a different team, or needs to be shared with others.

## CLI

The Docker CLI lets you interact with your Docker Compose applications through the `docker compose` command and its subcommands. If you're using Docker Desktop, the Docker Compose CLI is included by default.

Using the CLI, you can manage the lifecycle of your multi-container applications defined in the `compose.yaml` file. The CLI commands enable you to start, stop, and configure your applications effortlessly.

### Key commands 

To start all the services defined in your `compose.yaml` file:

```console
$ docker compose up
```

To stop and remove the running services:

```console
$ docker compose down 
```

If you want to monitor the output of your running containers and debug issues, you can view the logs with: 

```console
$ docker compose logs
```

To list all the services along with their current status:

```console
$ docker compose ps
```

For a full list of all the Compose CLI commands, see the [reference documentation](/reference/cli/docker/compose/).

## Illustrative example

The following example illustrates the Compose concepts outlined above. The example is non-normative.

Consider an application split into a frontend web application and a backend service.

The frontend is configured at runtime with an HTTP configuration file managed by infrastructure, providing an external domain name, and an HTTPS server certificate injected by the platform's secured secret store.

The backend stores data in a persistent volume.

Both services communicate with each other on an isolated back-tier network, while the frontend is also connected to a front-tier network and exposes port 443 for external usage.

![Compose application example](../images/compose-application.webp)

The example application is composed of the following parts:

- Two services, backed by Docker images: `webapp` and `database`
- One secret (HTTPS certificate), injected into the frontend
- One configuration (HTTP), injected into the frontend
- One persistent volume, attached to the backend
- Two networks

```yml
services:
  frontend:
    image: example/webapp
    ports:
      - "443:8043"
    networks:
      - front-tier
      - back-tier
    configs:
      - httpd-config
    secrets:
      - server-certificate

  backend:
    image: example/database
    volumes:
      - db-data:/etc/data
    networks:
      - back-tier

volumes:
  db-data:
    driver: flocker
    driver_opts:
      size: "10GiB"

configs:
  httpd-config:
    external: true

secrets:
  server-certificate:
    external: true

networks:
  # The presence of these objects is sufficient to define them
  front-tier: {}
  back-tier: {}
```

The `docker compose up` command starts the `frontend` and `backend` services, creates the necessary networks and volumes, and injects the configuration and secret into the frontend service.

`docker compose ps` provides a snapshot of the current state of your services, making it easy to see which containers are running, their status, and the ports they are using:

```text
$ docker compose ps

NAME                IMAGE                COMMAND                  SERVICE             CREATED             STATUS              PORTS
example-frontend-1  example/webapp       "nginx -g 'daemon of…"   frontend            2 minutes ago       Up 2 minutes        0.0.0.0:443->8043/tcp
example-backend-1   example/database     "docker-entrypoint.s…"   backend             2 minutes ago       Up 2 minutes
```

## What's next 

- [Try the Quickstart guide](/manuals/compose/gettingstarted.md)
- [Explore some sample applications](https://github.com/docker/awesome-compose)
- [Familiarize yourself with the Compose Specification](/reference/compose-file/_index.md)


---
## File: features-uses.md

---
description: Discover the benefits and typical use cases of Docker Compose for containerized application development and deployment
keywords: docker compose, compose use cases, compose benefits, container orchestration, development environments, testing containers, yaml file
title: Why use Compose?
weight: 20
aliases:
  - /compose/features-uses/
---

## Key benefits of Docker Compose

Using Docker Compose offers several benefits that streamline the development, deployment, and management of containerized applications:

- Simplified control: Define and manage multi-container apps in one YAML file, streamlining orchestration and replication.

- Efficient collaboration: Shareable YAML files support smooth collaboration between developers and operations, improving workflows and issue resolution, leading to increased overall efficiency.

- Rapid application development: Compose caches the configuration used to create a container. When you restart a service that has not changed, Compose reuses the existing containers. Reusing containers means that you can make changes to your environment quickly.

- Portability across environments: Compose supports variables in the Compose file. You can use these variables to customize your composition for different environments, or different users.

## Common use cases of Docker Compose

Compose can be used in many different ways. Some common use cases are outlined
below.

### Development environments

When you're developing software, the ability to run an application in an
isolated environment and interact with it is crucial. The Compose command
line tool can be used to create the environment and interact with it.

The [Compose file](/reference/compose-file/_index.md) provides a way to document and configure
all of the application's service dependencies (databases, queues, caches,
web service APIs, etc). Using the Compose command line tool you can create
and start one or more containers for each dependency with a single command
(`docker compose up`).

Together, these features provide a convenient way for you to get
started on a project. Compose can reduce a multi-page "developer getting
started guide" to a single machine-readable Compose file and a few commands.

### Automated testing environments

An important part of any Continuous Deployment or Continuous Integration process
is the automated test suite. Automated end-to-end testing requires an
environment in which to run tests. Compose provides a convenient way to create
and destroy isolated testing environments for your test suite. By defining the full environment in a [Compose file](/reference/compose-file/_index.md), you can create and destroy these environments in just a few commands:

```console
$ docker compose up -d
$ ./run_tests
$ docker compose down
```

### Single host deployments

Compose supports production deployments on single hosts. You can use
Compose to deploy applications to remote Docker hosts and manage
production-specific configurations.

For details on using production-oriented features, see
[Compose in production](/manuals/compose/how-tos/production.md).

## What's next?

- [Learn about the history of Compose](history.md)
- [Understand how Compose works](compose-application-model.md)
- [Try the Quickstart guide](../gettingstarted.md)


---
## File: history.md

---
title: History and development of Docker Compose
linkTitle: History and development
description: Explore the evolution of Docker Compose from v1 to v5, including CLI changes, YAML versioning, and the Compose Specification.
keywords: compose, compose yaml, swarm, migration, compatibility, docker compose vs docker-compose
weight: 30
aliases:
- /compose/history/
---

This page provides:
 - A brief history of the development of the Docker Compose CLI
 - A clear explanation of the major versions and file formats that make up Compose v1, v2, and v5
 - The main differences between Compose v1, v2, and v5

## Introduction

![Image showing the main differences between Compose v1, Compose v2, and Compose v5](../images/v1-versus-v2-versus-v5.png)

The diagram above highlights the key differences between Docker Compose v1, v2, and v5. Today, the supported Docker Compose CLI versions are Compose v2 and Compose v5, both of which are defined by the [Compose Specification](/reference/compose-file/_index.md).

The diagram provides a high-level comparison of file formats, command-line syntax, and supported top-level elements. This is covered in more detail in the following sections.

### Docker Compose CLI versioning

Compose v1 was first released in 2014. It was written in Python and invoked with `docker-compose`.
Typically, Compose v1 projects include a top-level `version` element in the `compose.yaml` file, with values ranging from `2.0` to `3.8`, which refer to the specific [file formats](#compose-file-format-versioning).

Compose v2, announced in 2020, is written in Go and is invoked with `docker compose`.
Unlike v1, Compose v2 ignores the `version` top-level element in the `compose.yaml` file and relies entirely on the Compose Specification to interpret the file.

Compose v5, released in 2025, is functionally identical to Compose v2. Its primary distinction is the introduction of an official [Go SDK](/manuals/compose/compose-sdk.md). This SDK provides a comprehensive API that lets you integrate Compose functionality directly into your applications, allowing you to load, validate, and manage multi-container environments without relying on the Compose CLI. To avoid confusion with the legacy Compose file formats labeled “v2” and “v3,” the versioning was advanced directly to v5.

### Compose file format versioning

The Docker Compose CLIs are defined by specific file formats. 

Three major versions of the Compose file format for Compose v1 were released:
- Compose file format 1 with Compose 1.0.0 in 2014
- Compose file format 2.x with Compose 1.6.0 in 2016
- Compose file format 3.x with Compose 1.10.0 in 2017

Compose file format 1 is substantially different to all the following formats as it lacks a top-level `services` key.
Its usage is historical and files written in this format don't run with Compose v2 or v5.

Compose file format 2.x and 3.x are very similar to each other, but the latter introduced many new options targeted at Swarm deployments.

To address confusion around Compose CLI versioning, Compose file format versioning, and feature parity depending on whether Swarm mode was in use, file format 2.x and 3.x were merged into the [Compose Specification](/reference/compose-file/_index.md). 

Compose v2 and v5 uses the Compose Specification for project definition. Unlike the prior file formats, the Compose Specification is rolling and makes the `version` top-level element optional. Compose v2 and v5 also makes use of optional specifications - [Deploy](/reference/compose-file/deploy.md), [Develop](/reference/compose-file/develop.md), and [Build](/reference/compose-file/build.md).

To make migration easier, Compose v2 and v5 has backwards compatibility for certain elements that have been deprecated or changed between Compose file format 2.x/3.x and the Compose Specification.

## What's next?

- [How Compose works](compose-application-model.md)
- [Compose Specification reference](/reference/compose-file/_index.md)


---
## File: _index.md

---
build:
  render: never
title: Introduction to Compose
weight: 10
---


---
## File: release-notes.md

---
title: Release notes
weight: 90
params:
  sidebar:
    goto: "https://github.com/docker/compose/releases"
---

---
## File: faq.md

---
description: Answers to common questions about Docker Compose, including v1 vs v2, commands, shutdown behavior, and development setup.
keywords: docker compose faq, docker compose questions, docker-compose vs docker compose, docker compose json, docker compose stop delay, run multiple docker compose
title: Frequently asked questions about Docker Compose
linkTitle: FAQs
weight: 10
tags: [FAQ]
aliases:
- /compose/faq/
---

### What is the difference between `docker compose` and `docker-compose`

Version one of the Docker Compose command-line binary was first released in 2014. It was written in Python, and is invoked with `docker-compose`. Typically, Compose v1 projects include a top-level version element in the `compose.yaml` file, with values ranging from 2.0 to 3.8, which refer to the specific file formats.

Version two of the Docker Compose command-line binary was announced in 2020, is written in Go, and is invoked with `docker compose`. Compose v2 ignores the version top-level element in the compose.yaml file.

Compose v5, released in 2025, uses the same `docker compose` command and is functionally identical to Compose v2. Its primary distinction is the introduction of an official [Go SDK](/manuals/compose/compose-sdk.md).

For further information, see [History and development of Compose](/manuals/compose/intro/history.md).

### What's the difference between `up`, `run`, and `start`?

Typically, you want `docker compose up`. Use `up` to start or restart all the
services defined in a `compose.yaml`. In the default "attached"
mode, you see all the logs from all the containers. In "detached" mode (`-d`),
Compose exits after starting the containers, but the containers continue to run
in the background.

The `docker compose run` command is for running "one-off" or "adhoc" tasks. It
requires the service name you want to run and only starts containers for services
that the running service depends on. Use `run` to run tests or perform
an administrative task such as removing or adding data to a data volume
container. The `run` command acts like `docker run -ti` in that it opens an
interactive terminal to the container and returns an exit status matching the
exit status of the process in the container.

The `docker compose start` command is useful only to restart containers
that were previously created but were stopped. It never creates new
containers.

### Why do my services take 10 seconds to recreate or stop?

The `docker compose stop` command attempts to stop a container by sending a `SIGTERM`. It then waits
for a [default timeout of 10 seconds](/reference/cli/docker/compose/stop/). After the timeout,
a `SIGKILL` is sent to the container to forcefully kill it. If you
are waiting for this timeout, it means that your containers aren't shutting down
when they receive the `SIGTERM` signal.

There has already been a lot written about this problem of
[processes handling signals](https://medium.com/@gchudnov/trapping-signals-in-docker-containers-7a57fdda7d86)
in containers.

To fix this problem, try the following:

- Make sure you're using the exec form of `CMD` and `ENTRYPOINT`
in your Dockerfile.

  For example use `["program", "arg1", "arg2"]` not `"program arg1 arg2"`.
  Using the string form causes Docker to run your process using `bash` which
  doesn't handle signals properly. Compose always uses the JSON form, so don't
  worry if you override the command or entrypoint in your Compose file.

- If you are able, modify the application that you're running to
add an explicit signal handler for `SIGTERM`.

- Set the `stop_signal` to a signal which the application knows how to handle:

  ```yaml
  services:
    web:
      build: .
      stop_signal: SIGINT
  ```

- If you can't modify the application, wrap the application in a lightweight init
system (like [s6](https://skarnet.org/software/s6/)) or a signal proxy (like
[dumb-init](https://github.com/Yelp/dumb-init) or
[tini](https://github.com/krallin/tini)).  Either of these wrappers takes care of
handling `SIGTERM` properly.

### How do I run multiple copies of a Compose file on the same host?

Compose uses the project name to create unique identifiers for all of a
project's containers and other resources. To run multiple copies of a project,
set a custom project name using the `-p` command line option
or the [`COMPOSE_PROJECT_NAME` environment variable](/manuals/compose/how-tos/environment-variables/envvars.md#compose_project_name).

### Can I use JSON instead of YAML for my Compose file?

Yes. [YAML is a superset of JSON](https://stackoverflow.com/a/1729545/444646) so
any JSON file should be valid YAML. To use a JSON file with Compose,
specify the filename to use, for example:

```console
$ docker compose -f compose.json up
```

### Should I include my code with `COPY`/`ADD` or a volume?

You can add your code to the image using `COPY` or `ADD` directive in a
`Dockerfile`.  This is useful if you need to relocate your code along with the
Docker image, for example when you're sending code to another environment
(production, CI, etc).

Use a `volume` if you want to make changes to your code and see them
reflected immediately, for example when you're developing code and your server
supports hot code reloading or live-reload.

There may be cases where you want to use both. You can have the image
include the code using a `COPY`, and use a `volume` in your Compose file to
include the code from the host during development. The volume overrides
the directory contents of the image.


---
## File: feedback.md

---
description: Find a way to provide feedback on Docker Compose that's right for you 
keywords: Feedback, Docker Compose, Community forum, bugs, problems, issues
title: Give feedback
weight: 20
---

There are many ways you can provide feedback on Docker Compose.

### Report bugs or problems on GitHub

To report bugs or problems, visit [Docker Compose on GitHub](https://github.com/docker/compose/issues)

### Feedback via Community Slack channels

You can also provide feedback through the `#docker-compose` [Docker Community Slack](https://dockr.ly/comm-slack) channel. 


---
## File: _index.md

---
build:
  render: never
title: Support and feedback
weight: 80
---

---
## File: trust-model.md

---
title: Trust model for Compose files
weight: 70
description: Learn how Docker Compose treats Compose files as trusted input and what this means when using files you did not author.
keywords: compose, security, trust model, oci, remote, registry, include, extends, supply chain, trust, best practices
---

Docker Compose treats every Compose file as trusted input. When a Compose file
requests elevated privileges, host filesystem access, or any other
configuration, Compose applies it as written. This is the same behavior as
passing flags directly to `docker run`.

This means that any Compose file you run, whether it lives on your local
filesystem, in a Git repository, or in an OCI registry, has full control over
how containers interact with your host. The security boundary is not where the file comes from but whether you trust the author.

Evaluating trust means asking: Who authored this file? Has it changed since you last reviewed it? Do you understand every privilege it requests?

## The dependency chain

A Compose application can be assembled from multiple sources. The
[`include`](/reference/compose-file/include.md) directive imports entire Compose
files, while [`extends`](/reference/compose-file/services.md#extends) inherits
configuration from a specific service in another file. Both support remote
references and can be chained:

```text
Your command
  └─ compose.yaml                                    (local or remote)
       ├─ services, volumes, networks                (direct config)
       ├─ include:
       │    └─ oci://registry.example.com/base:v2   (remote dependency)
       │         └─ services, volumes, networks      (indirect config)
       └─ services:
            └─ app:
                 └─ extends:
                      └─ file: oci://registry.example.com/templates:v1
                           └─ service: webapp        (inherited config)
```

Each level has the same capabilities. The top-level file you inspect may appear
safe while a nested `include` or `extends` introduces services with elevated
privileges, host bind mounts, or untrusted images. These dependencies can also
change independently. Risky settings can be introduced by a nested dependency that you never
see unless you inspect the fully resolved output.

> [!IMPORTANT]
>
> Compose warns you when a configuration references remote sources. Do not
> accept this without understanding every reference in the chain.

## Best practices

### Inspect the full configuration

To see exactly what Compose applies, including all resolved `includes`,
`extends`, merged overrides, and interpolated variables, use:

```console
$ docker compose config
```

For remote references:

```console
$ docker compose -f oci://registry.example.com/myapp:latest config
```

Review this output before running `up` or `create`, especially when the
configuration comes from a source you have not audited.

#### Fields to look out for

A Compose configuration has broad control over how containers interact with the
host. The following is a non-exhaustive list of fields that carry security
implications when set by an untrusted author:

| Field | Effect |
|-------|--------|
| `privileged` | Grants the container full access to the host |
| `cap_add` | Adds Linux capabilities such as `SYS_ADMIN` or `NET_RAW` |
| `security_opt` | Configures security profiles including seccomp and AppArmor |
| `volumes` / bind mounts | Mounts host directories into the container |
| `network_mode: host` | Shares the host network stack |
| `pid: host` | Shares the host PID namespace |
| `devices` | Exposes host devices to the container |
| `image` | Pulls and runs an arbitrary container image |
| `env_file`, `label_file`, `secrets`/`configs` (`file:`), `include`, `extends` | Read files from the host, directly or through symlinks resolved from a remote checkout, and can surface their contents during configuration loading |
| `provider` | Runs the binary named by `provider.type` on the host, outside any container, when you run `up`, `down`, or `stop` |

When in doubt, look up the effect of any unfamiliar field before running the configuration.

Like `volumes`, the file-reference fields read any file the user running Compose
can access, including through symlinks resolved from a remote checkout, and their
contents can appear in `docker compose config` output before any container starts.
Compose does not confine reads to the project directory. Treat a Compose project as
code you run, not data you inspect.

### CI/CD environments

Automated pipelines are particularly sensitive because they often run with
access to credentials, cloud provider tokens, or Docker sockets.

- Avoid referencing public or unverified Compose configurations in automated
  pipelines.
- Gate updates behind your normal code review process.
- Use read-only Docker socket mounts where possible to limit your risk.

### Pin remote references to digests

Tags are mutable, meaning anyone with push access to a registry can overwrite a tag silently, so a reference you reviewed last week may point to different content today.

Digests are immutable. Instead of referencing by tag, pin to the digest. 

```yaml
include:
  - oci://registry.example.com/base@sha256:a1b2c3d4...
```

Treat any update to a pinned digest as a code change. Make sure you review the new content before updating the reference.

### Other

- Use a private registry: Host OCI artifacts on a registry your
  organization controls. Restrict who can push to it.
- Audit transitive dependencies: Check every remote `include` and `extends`
  reference in the chain, not just the top-level file.
- Review all Compose confirmation prompts: When loading remote Compose files,
  Compose displays confirmation prompts for interpolation variables, environment
  values, and remote includes. Review these before accepting.

## Further reading

- [OCI artifact applications](/manuals/compose/how-tos/oci-artifact.md)
- [Use Compose in production](/manuals/compose/how-tos/production.md)
- [`include` reference](/reference/compose-file/include.md)
- [`extends` reference](/reference/compose-file/services.md#extends)
- [Manage secrets in Compose](/manuals/compose/how-tos/use-secrets.md)