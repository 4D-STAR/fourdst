# `fourdst-cli` Documentation

`fourdst`'s goal is to provide a single source for installation and utility for all lib* utilities. This includes python bindings and a command line interface for common tasks. This document covers the design and usage of that command line interface, `fourdst-cli`

At the moment `fourdst-cli` only includes subprograms and commands related to plugin management for the 4D-STAR/libplugin library. [libplugin](https://github.com/4D-STAR/libplugin) is a small plugin library written for use by the 4D-STAR collaboration. Its goal is to allow researchers to easily share plugins to extend code in a low friction and reproducible manner.

> **IMPORTANT:** Plugins, by their nature, allow arbitrary code to run on your system, libplugin does not preform any kind of sandboxing so this has the potential to be *very* unsafe. We have built in a rudimentary signing system to provide at least some security. However, the developers are researchers and not security professionals. As a user, please listen to the warnings you get. Self-signed bundles are fine for you to use for yourself; however, be very, very weary of unsigned or untrusted bundles when you are not the author. libplugin was developed for scientific use and with a focus on ease of use for scientists (and with the paradigm of collaborates sharing plugin files). This means that the security model does have some implicit level of trust assumed. Use this library at your own risk and **be very careful** about using unknown plugins.

## Installation
`fourdst-cli` can be installed from pip

```bash
pip install fourdst
```

or from source

```
git clone https://github.com/4D-STAR/fourdst
cd fourdst
pip install .
```

note that in order to install from source you will need `meson`, `ninja`, and `cmake` installed. If you do not have these, they can all be installed with pip

```bash
pip install meson ninja cmake
```

Installing `fourdst` will make the `fourdst-cli` command line program available. Note you may need to restart or resource your terminal for changes to take effect.


## Core Concepts
There are few concepts `fourdst-cli` defined, these are outlined below.

### Plugins
A **Plugin** is a self-contained C++ project, built as a shared library (`.so`, `.dylib`), that implements a specific interface defined in a C++ header file. The `fourdst-cli` helps scaffold, build, and manage these projects. Generally, plugin consumers (programs that can make use of user plugins) must provide interface header files which can then be targeted by plugin authors.

### Bundles (`.fbundle`)
A **Bundle** is a single `.fbundle` file (which is just a standard `.zip` archive using a different extension) that contains everything needed to distribute one or more plugins. A key design principle is that a bundle can contain both pre-compiled binaries for various platforms *and* the full source code. This hybrid approach provides the best of both worlds:
- **Convenience**: Users can often use a pre-compiled binary directly if one matches their system, which is fast and requires no local toolchain.
- **Flexibility & Longevity**: If a compatible binary isn't available, users can compile the plugin from the included source code. This ensures the plugin remains usable on future platforms.

### ABI (Application Binary Interface)
The C++ ABI is a complex and often frustrating aspect of cross-platform development. It defines how compiled code interacts at a binary level. Different compilers (GCC, Clang, MSVC), standard libraries (libstdc++, libc++), and even compiler versions can produce ABI-incompatible binaries.

**Why it matters:** You cannot simply mix and match C++ binaries compiled with different toolchains. `fourdst-cli` tackles this head-on by performing a one-time **ABI detection** on the host system. It compiles and runs a small C++ program to determine the exact compiler, standard library, and ABI flags. This generates a unique **ABI Signature** (e.g., `clang-libc++-1500.3.9.4-libc++_abi`) which is used to tag binaries, ensuring that only compatible libraries are loaded.

### The Trust Store
To ensure security, `fourdst-cli` uses a cryptographic trust model based on public-key cryptography.
- **Signing**: Plugin authors can sign their bundles with a private key. This process adds the author's public key fingerprint to the bundle's manifest and creates a digital signature (`manifest.sig`).
- **Verification**: Consumers of the bundle add the author's public key to their local **Trust Store** (`~/.config/fourdst/keys`). When they inspect the bundle, the CLI checks if the signature is valid and if the key that created it is in the local trust store. This confirms both the bundle's integrity (it hasn't been tampered with) and its authenticity (it comes from a trusted author).

---

## Command Reference
All commands and subprograms can display more detailed cli api by passing the `--help` flag. 

### `plugin`
Subprogram for managing individual plugin projects.

#### `plugin init`
Initializes a new Meson-based C++ plugin project from a C++ header file that defines an interface.

```bash
fourdst-cli plugin init <PROJECT_NAME> --header <PATH_TO_HEADER>
```

> The init command automates the tedious setup of a C++ project. It parses the header to find abstract classes (those with pure virtual methods) and generates a C++ source file with stubs for all the methods you need to implement. It also sets up a complete meson.build file with the fourdst/libplugin dependency, and initializes a Git repository, so you can start coding immediately.

#### `plugin validate`

Validates the structure of a plugin directory.

```bash
fourdst-cli plugin validate [PLUGIN_PATH]
```

> This is a crucial command for quality assurance and continuous integration (CI). It quickly checks for common project structure errors, like a missing meson.build file or the absence of a shared_library() definition, before you attempt a full build.

#### `plugin extract`

Extracts a plugin's source code from a bundle.

```bash
fourdst-cli plugin extract <PLUGIN_NAME> <BUNDLE_PATH> --out <OUTPUT_DIR>
```

> This allows developers to easily inspect the source code of a plugin contained within a bundle without having to manually unzip multiple archives.

#### `plugin diff`

Compares the source code of a specific plugin between two different bundles.

```bash
fourdst-cli plugin diff <PLUGIN_NAME> <BUNDLE_A_PATH> <BUNDLE_B_PATH>
```

> This is an essential tool for understanding what changed between two versions of a plugin bundle, providing a "git diff" like experience for the plugin's source code.

### `bundle`

Commands for creating, signing, and managing distributable .fbundle files.

#### `bundle create`

Builds and packages one or more plugin projects into a single .fbundle file.

```bash
fourdst-cli bundle create <PLUGIN_DIR_1> [PLUGIN_DIR_2...] --out my_bundle.fbundle
```

> Why it's designed this way: This is the primary command for authors. It automates the entire packaging process:
>
>    1. Compiles the plugin(s) for the host system.
>
>    2. Tags the resulting binary with the host's platform and ABI signature.
>
>    3. Packages the complete source code (respecting .gitignore) into a source distribution (sdist).
> 
>    4. Creates a manifest.yaml file describing the contents.
>
>    5. Zips everything into a single, portable .fbundle file.

#### `bundle inspect`

Inspects a bundle, validating its contents and cryptographic signature.

```bash
fourdst-cli bundle inspect <BUNDLE_PATH>
```

> This is the most important command for consumers. It provides a complete "report card" for a bundle:
>
>    - Trust Status: It checks for a signature, verifies it against the manifest, and checks if the signing key is in your local trust store. It will clearly state if the bundle is SIGNED and TRUSTED, SIGNED but UNTRUSTED, or UNSIGNED.
>
>    - Content Validation: It verifies that all files listed in the manifest actually exist in the archive and checks their checksums if the bundle is signed.
>
>    - Compatibility: It lists all available binaries and highlights whether one is compatible with your current system's platform and ABI.

#### `bundle sign`

Signs a bundle with an author's private key.

```bash
fourdst-cli bundle sign <BUNDLE_PATH> --key /path/to/private_key
```

> Security and authenticity are paramount. This command adds a cryptographic layer of trust to the bundle. It calculates checksums for all binary files, adds them to the manifest, and then signs the entire manifest. This makes the bundle tamper-proof; any modification to the manifest or the binary files will invalidate the signature.

#### `bundle validate`

Performs a strict validation of a bundle file or a pre-bundle directory.

```bash
fourdst-cli bundle validate <PATH_TO_BUNDLE_OR_DIR>
```

> While inspect provides a user-friendly report, validate is a stricter check suitable for automated scripts. It returns a non-zero exit code if any error is found (missing files, checksum mismatches, invalid manifest), making it ideal for CI/CD pipelines.

#### `bundle clear`

Removes all compiled binaries from a bundle, leaving only the source distributions.

```bash
fourdst-cli bundle clear <BUNDLE_PATH>
```

> This is useful for creating a "source-only" distribution. It reduces the file size and removes any potentially untrusted pre-compiled code, forcing the consumer to build from source.

#### `bundle diff`

Compares two bundle files, showing differences in their manifests, signatures, and file contents.

```bash
fourdst-cli bundle diff <BUNDLE_A_PATH> <BUNDLE_B_PATH>
```

> Provides a high-level overview of what has changed between two bundle releases, including changes to the manifest, the signature, and which files have been added, removed, or modified.

#### `bundle fill`

Builds new binaries for missing targets from the bundle's source.

```bash
fourdst-cli bundle fill <BUNDLE_PATH>
```

> This is the magic that makes cross-platform distribution feasible. If a user receives a bundle without a binary for their specific platform (e.g., they are on aarch64-linux and the bundle only has an x86_64-linux binary), they can run bundle fill. The command will:
>
>   - Detect available build targets (native, cross-compilation files, Docker).
>
>   - Prompt the user to select which missing binaries they want to build.
>
>   - Unpack the source, compile it using the selected target, and add the newly compiled, correctly tagged binary back into the bundle.
>
>   - This empowers end-users to create binaries for their own platform without needing to be a C++ expert.

### `keys`

Commands for managing cryptographic keys and the trust store.

- `keys generate`: Creates a new Ed25519 key pair for signing.

- `keys add <KEY_PATH>`: Adds a public key to the local trust store.

- `keys remove [KEY_PATH]`: Removes a public key from the trust store.

- `keys list`: Lists all trusted public keys.

#### `keys sync`

Syncs the local trust store with all configured remote Git repositories.

> Manually adding keys can be cumbersome. This command allows you to point the CLI to one or more Git repositories that contain public keys. Running keys sync will pull the latest keys from all remotes, making it easy to keep your trust store up-to-date with keys from your team or community.

### `keys remote`

Manages the list of remote key repositories.

-  `keys remote add <URL> <NAME>`: Adds a new remote Git repository.

- `keys remote list`: Lists configured remotes.

- `keys remote remove <NAME>`: Removes a remote.

> The usage of `keys remote` is intended to allow for remote source of trust to be established. There are risks associated with this as it shifts the expectation of trust onto the repository maintainers. Users should use remote public key stores at their own risk. 

> **Note:** We intend to establish a public key store on GitHub where plugin authors, officially vetted by the 4D-STAR collaboration, can register their public keys. <span style="color:red">**Any other public key stores for libplugin are unofficial and should be treated with extreme caution**</span>.

### `cache`

Commands for managing the local cache.

#### `cache clear`

Clears all cached data, including the detected ABI signature.

> The ABI signature is cached for performance. If you update your system's C++ compiler or toolchain, the cached ABI might become stale. cache clear deletes the cache, forcing a re-detection on the next run, ensuring your builds are always using the correct ABI signature.

## Workflows

### Workflow 1: Plugin Author (From Idea to Signed Bundle)

#### 1. Define the Interface:
Create a C++ header file, my_interface.h, with a class containing pure virtual methods.

#### 2. Initialize the Project:

```bash
fourdst-cli plugin init my_awesome_plugin --header my_interface.h

cd my_awesome_plugin
```

#### 3. Implement the Logic:
Open src/my_awesome_plugin.cpp and fill in the `TODO` sections with your plugin's implementation.

#### 4. Build and Test Locally:

```bash
meson setup builddir
meson compile -C builddir
```

#### 5. Create the Bundle:
From the parent directory of my_awesome_plugin run

```bash
fourdst-cli bundle create my_awesome_plugin --out my_plugin_v1.fbundle
```

#### 6. Generate a Signing Key (only needs to be done once):

```bash
fourdst-cli keys generate --name my_author_key
```

#### 7. Install your self signing key (only needs to be done once)
```bash
fourdst-cli keys add my_author_key.pub
```
This will install the key you generated to your fourdst config (`$HOME/.config/fourdst/keys`). This lets you easily use self-signed bundles. Note that you should **not** simply self sign bundles from the internet.

#### 8. Sign the Bundle:

```bash
fourdst-cli bundle sign my_plugin_v1.fbundle --key my_author_key
```

#### 8. Distribute: 
As said at the top of this document the intended usage case of libplugin is something like "I am a researcher and I have this set of plugins I wrote for this code, I want my student, or collaborator, to be able to run the same code with the same set of plugins". Because of this we anticipate that usage will look like individual researchers building plugins and bundles and sharing them directly with others (i.e. not through some central distribution server).

Plugin authors can register their public signing keys with us to establish a trusted set of authors (Note: that each author must be validated manually by current authors). This lets plugin consumers compare signed bundles to trusted sources.

> We want to remind readers of the note at the top. The authors of this library are researchers and not security professionals. libplugin has been developed with the goal of making plugins easy for scientists and with a limited amount of security tooling built in; however, plugins should be treated as untrusted code and should only be used if you are **very** confident that you trust the author and that the plugin you have is actually from that author (and has not been modified or had malicious code injected into it).

### Workflow 2: Plugin Consumer (Verifying and Using a Bundle)

#### 1. Receive Files
You get my_plugin_v1.fbundle from an author. Either the author is a trusted author (at which point you can call fourdst-cli keys sync to synchronize trusted keys with the 4D-STAR GitHub keychain) or they are not. If they are not they can choose to share the public key of the key pair used to sign the bundle. 

> Note: You must be **very** sure you trust the plugin author if you accept their public key. Arbitrary code signed with the private key of this pair will be able to run on your compute. **Do not accept random public keys from plugin authors on the internet**. This is intended to be used by trusted collaborators, advisors, or other personal / professional connections. 

Assuming you do trust the author...

#### 2. Add the author's public key to your local trust store.

```bash
fourdst-cli keys add /path/to/my_author_key.pub
```

#### 3. Inspect the Bundle:
Verify the signature and check for a compatible binary.

```bash
fourdst-cli bundle inspect my_plugin_v1.fbundle
```

- **Scenario A:** Compatible binary exists. The output shows Trust Status: ✅ SIGNED and TRUSTED and highlights a compatible binary in green. You are ready to use the plugin.

- **Scenario B:** No compatible binary. The output shows the bundle is trusted, but warns that no binary matches your system's ABI.

- **Scenario C:** Untrusted or unsigned

#### 4a. (Optional) Fill the Bundle:
If you are in Scenario B, build the binary from the included source

```bash
fourdst-cli bundle fill my_plugin_v1.fbundle
```

- The CLI will prompt you to build for your native platform. After it finishes, running bundle inspect again will show a new, compatible binary. The bundle is now ready to use.

#### 4b. (Optional) Sign the Bundle:
If you are in Scenario C, and **if you trust the author and are confident that the author you think sent you the plugin *actually* sent you the plugin** you may choose to self sign the plugin.

Note that this increases your risk of running malicious code, you are effectively saying "I trust this code regardless of the fact that no chain of trust can be established". If you accept that risk you can choose to sign the code yourself. Follow the instructions in the above workflow to do this.


#### 5. Use the bundle
Whatever code you have that uses libplugin for plugins will expect the bundle path to be provided somehow (this might be through a command line option, config file, or some other manner). Pass the filled, signed, and validated bundle to this program.

