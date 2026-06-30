import { describe, it, expect, afterEach } from "vitest";
import { isSmsConfigured, getSmsSender, sendSmsOtp } from "./sms";

afterEach(() => {
  delete process.env.SMS_PROVIDER;
});

describe("SMS 2FA interface — unconfigured by default (v3)", () => {
  it("reports not configured with no provider", () => {
    expect(isSmsConfigured()).toBe(false);
    expect(getSmsSender()).toBeNull();
  });

  it("sendSmsOtp rejects when unconfigured (never silently drops a code)", async () => {
    await expect(sendSmsOtp("+15555550100", "123456")).rejects.toThrow(/not configured/);
  });

  it("a wired-but-unimplemented provider fails loud rather than silently", () => {
    process.env.SMS_PROVIDER = "twilio";
    expect(isSmsConfigured()).toBe(true);
    expect(() => getSmsSender()).toThrow(/no SMS sender implementation/);
  });
});
