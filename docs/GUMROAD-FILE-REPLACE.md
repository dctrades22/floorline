# Gumroad file replace

Read on 2026-10-23 from the live help pages. Quotes are the text returned that day. Anything the pages do not say is marked UNCONFIRMED. This note does not change a Gumroad product.

## What buyers see

Adding a product, https://gumroad.com/help/article/149-adding-a-product

> Your customers will see the product just as you see it in the editor, both on a browser and our mobile app as well!

The page describes the Content tab (files, pages, folders, versions) and Publish. It does not say that replacing a file sends an email.

I'm not receiving updates, https://gumroad.com/help/article/211-im-not-receiving-updates.html

> In your Library, you can quickly access all of your purchases and any updates associated with them. Just click on the product's card and you'll see the product's up-to-date files and posts.

The same page is about a buyer who opted out of creator communication. Resubscribe is how they "start receiving the creator’s posts and updates again." It does not say a Content-tab file replacement itself sends mail.

Your Gumroad Library, https://gumroad.com/help/article/198-your-gumroad-library

The library is where purchases are listed. It does not, in the text fetched on 2026-10-23, say that a replaced file is pushed to a copy the buyer already downloaded.

UNCONFIRMED: whether a file already saved on the buyer's disk is updated in place. The Library sentence says the card shows up-to-date files. It does not say an old download changes.

## Versions

Setting up versions, https://gumroad.com/help/article/126-setting-up-versions-on-a-digital-product

> This does not charge or refund the customer, it simply grants them access to the files for the new version.

Content is attached per version on the Content tab. Deleting a version falls back to the cheapest version's content, or to product-level content if no version remains. Reassign from the Sales dashboard.

## Notifying buyers

Workflows, https://gumroad.com/help/article/131-using-workflows-to-send-automated-updates

Workflows send scheduled emails on a trigger. The triggers named on 2026-10-23 are: Purchase, New subscriber, Member cancels, New affiliate, Abandoned cart. A "file replaced" trigger is not listed.

> Note: You cannot send emails until you've earned $100 after fees and received a payout.

Starting an email newsletter, https://gumroad.com/help/article/170-audience

> To send out an email to your followers, you can go to your Emails dashboard and click New Email in the top right-hand corner.
>
> Under Audience, you can choose to send this email to your Subscribers only, to your Customers only, Affiliates only, or to Everyone.

That is a separate publish/schedule action. The page does not say replacing a product file starts this email.

Memberships, https://gumroad.com/help/article/82-membership-products (membership products, not this one-time file):

> You can use our Emails feature to update customers about new files being added or any changes to the membership in general.

UNCONFIRMED for this one-time digital product: that replacing the xlsx emails existing buyers automatically. No fetched page says that it does. The pages that discuss telling customers about new files describe Emails or Workflows as a step the seller takes. Treat automatic notification as not documented, and send an Email to Customers (or resend the receipt from the sale) if buyers should be told.

Supporting customers, https://gumroad.com/help/article/352-supporting-your-customers

Receipts can be resent. "Posts and workflow emails can only be resent to customers who are still subscribed to your emails; if a customer has unsubscribed, receipts are the only emails you can resend to them."

## API

https://gumroad.com/api , PUT `/v2/products/:id`, read 2026-10-23:

> Update an existing product. Send only the fields you want to change. Sending `files`, `tags`, or `rich_content` replaces the entire collection.

> files (optional) array of files; full replacement — see Attaching to a product for how to keep existing files

UNCONFIRMED: whether an API file replace notifies buyers. The API text does not say it does.

## Steps for this product

1. Download the current Gumroad file and archive it locally with the date before replacing it.
2. Edit the product, or the version buyers actually own. Replace the xlsx on the Content tab. Publish.
3. Open a receipt or a Library card and confirm the new file downloads. Compare its SHA-256 to the tested file.
4. Do not assume buyers were emailed. Send an Email to Customers describing the Instrument column, the calculated tick, and the separate mini and micro caps. Resend a receipt only when a buyer needs the mail again.
5. Buyers who already filled the old workbook do not get the new formulas inside that file. They start from the new download.
