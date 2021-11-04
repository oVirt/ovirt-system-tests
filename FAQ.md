# FAQ

Here you can find some frequently asked questions about OST.

## How to test your OST patch with OST?
Post a `ci ost` comment on your patch in gerrit.

## How to test your non-OST patch (i.e. a vdsm, ovirt-engine patch) with OST?
Non-OST patches run OST automatically once the patch is approved and verified.

## My OST patch build is failing and I don't know why. Where can I get some further information?
When an OST run fails for your patch, you should see a comment posted that says 'Patch Set X: OST-1'.<br>
There you will find a link to the failing job with the job id.
In that link, accessing the 'console output' would gain you some more information.

## Where can I get some further information for a failed gating job?
Gating job is being created as part of testing your patch with OST, by posting a `ci ost` comment on your OST patch in gerrit (or `ci test` comment for a non-OST patch).<br>
You should see a comment posted that says 'https://redir.apps.ovirt.org/dj/job/ds-ost-gating-ost/XYZ : the-relevant-suite : FAILURE'.
Pressing on that link, will redirect you to the failing job in the 'ds-ost-gating-ost' project, where you can see the d/s job triggered in 'ds-ost-baremetal-ost'.<br>
By pressing the associated job number, you'll be able to explore the 'console output', or access the 'configuration matrix' at the bottom of the screen.
