/**
 * @param {puppeteer.Browser} browser
 * @param {{url: string, options: LHCI.CollectCommand.Options}} context
 */
module.exports = async (browser, context) => {
    // launch browser for LHCI
    const page = await browser.newPage();
    await page.goto('http://localhost:8000/account/login');
    await page.type('#id_username', 'admin');
    await page.type('#id_password', 'admin');
    await page.click('[type="submit"]');
    await page.waitForNavigation();
    // close session for next run
    await page.close();
};