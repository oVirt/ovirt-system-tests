# FAQ

Here you can find some frequently asked questions about OST.

## How to test your OST patch with OST?
Post a `/ost` comment on your patch in GitHub.

## How to test your non-OST patch (i.e. a vdsm, ovirt-engine patch) with OST?
All non-OST patches can be tested posting the comment /ost in your GitHub patch.

## My OST patch build is failing and I don't know why. Where can I get some further information?
When an OST run fails for your patch, you should see in the PR, 'All checks have failed,<BR>1 failing check'.<br>
OST Failing after Xm<BR>
Click on 'Details'.<BR>
There you will find a link to the failing job with the job id.
In that link, accessing the 'console output' would gain you some more information.
