# github OST automation

*workflows/ost.yaml* - reusable workflow job, referred from individual projects

*example-trigger.yaml* - example how to invoke from projects

*jenkins* file contains the code on jenkins side in 2 sections
- Build Trigger
  - configure with SCM Build trigger use "[ScriptTrigger] - Poll with a shell or batch script". Paste the first part only, provide IP= at the top
- Actual job steps
  - initial step - paste first and second part together. You must provide IP= and RHEL= strings at the top, and in Build Environment use secret file OST_APP_PRIVATE_KEY_FILENAME
  - inject variables from "vars"
  - conditinal step(multiple) if build is still succeeding at this point
    - for ost-images runs only
        - build specific ost-image first when CUSTOM_OST_IMAGES is set to a string "build-me-some". Will be filled in by build-image job for the respective ost-images refspec from PR
        - inject vars again, overriding OST_REFSPEC to empty (to run stock basic-suite-master code) and CUSTOM_OST_IMAGES set to the resulting repo from build-image
    - call out the actual OST job with CUSTOM_REPOS=${PR_URL} and OST_IMAGE=${OST_IMAGE} set
    - processing step - paste second part only, and make sure it gets executed regardless the OST job result

*nginx* contains manual installation steps on a self-hosted runner, with matching label in ost.yaml
