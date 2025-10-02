## Packaging
We publish new updates as docker containers to the GitHub container repository. To do this we use a workflow that automatically builds the container and releases it.

For added security, packages will only be released if the triggering tag is signed by one of the approved GPG keys.

### Adding your key
To add your key to the repository you will need to have contributor permissions for the repo and the GitHub CLI installed on your machine and authenticated to your account.

1. Export your gpg key with ASCII armour.
```bash
gpg -a --export <Key ID/Name> > packaging-key.asc
```
2. Encode your key with base64
```bash
cat packaging-key.asc | base64 `> encoded-key.asc
```
3. Upload it to GitHub secrets
```bash
gh secret set <Name of key> < encoded-key.asc
```
4. Add the key to the workflow to be imported
```yml
- name: Verify tag signature
  run: |
      echo "${{ secrets.DEVELOPER_KEY }}" | base64 --decode > dev-public-key.gpg
      gpg -q --import dev-public-key.gpg
      echo "${{ secrets.<Name of key> }}" | base64 --decode > <your-key>.gpg
      gpg -q --import <your-key>.gpg
      ...
      rm -f dev-public-key.gpg
      rm -f <your-key>.gpg
```

### Publishing a package
To publish a package you need to tag a commit.
1. Make sure you are on the main branch
2. Create a signed tag. NOTE: The tag name must be the version name following the [semantic versioning](https://semver.org/) standard with a leading `v`.
```bash
git tag -as vM.m.p -m ""
```
3. Push the tag to origin
```bash
git push --tags
```

This should trigger the workflow, if it doesn't, make sure that your tag is named correctly and is on the main branch.
If the workflow fails either the container couldn't build or the tag wasn't signed by a valid key.
