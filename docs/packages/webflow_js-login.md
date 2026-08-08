<< WEBFLOW.JS >>
// packages/systems/users/siteBundles/login.ts
  var login_exports = {};
  __export(login_exports, {
    asyncLogInUser: () => asyncLogInUser,
    handleLogInForms: () => handleLogInForms,
    handleLoginRedirects: () => handleLoginRedirects
  });
  function getLoginLinks() {
    return Array.prototype.slice.call(document.links).filter((link) => link.getAttribute("href") === "/log-in");
  }
  function handleLoginRedirects() {
    getLoginLinks().forEach((link) => {
      const queryString = window.location.search;
      const redirectParam = queryString.match(/\?usredir=([^&]+)/g);
      if (redirectParam) {
        link.href = link.href.concat(redirectParam[0]);
      }
    });
  }
  function getLoginForms() {
    const loginForms = document.querySelectorAll(loginFormQuerySelector);
    return Array.prototype.slice.call(loginForms).filter((loginForm) => loginForm instanceof HTMLFormElement);
  }
  function handleLogInForms() {
    getLoginForms().forEach((loginForm) => {
      loginForm.addEventListener("submit", (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        if (!(form instanceof HTMLFormElement)) {
          return;
        }
        const submit = form.querySelector('input[type="submit"]');
        const submitText = disableSubmit(submit);
        hideElement(errorState);
        const emailInput = form.querySelector(
          `input[${USYS_DATA_ATTRS.inputType}="${USYS_INPUT_TYPES.email}"]`
        );
        const passwordInput = form.querySelector(
          `input[${USYS_DATA_ATTRS.inputType}="${USYS_INPUT_TYPES.password}"]`
        );
        if (!(emailInput instanceof HTMLInputElement) || !(passwordInput instanceof HTMLInputElement)) {
          return;
        }
        const onSuccessRedirectUrl = form.getAttribute(
          USYS_DATA_ATTRS.redirectUrl
        );
        asyncLogInUser(emailInput.value, passwordInput.value).then(() => {
          handleRedirect(onSuccessRedirectUrl);
        }).catch((error) => {
          resetSubmit(submit, submitText);
          if (errorState) {
            const elementErrorCode = error?.graphQLErrors?.[0]?.code ?? "";
            const errorCode = getLogInErrorCode(elementErrorCode);
            handleErrorNode(
              errorMsgNode,
              // @ts-expect-error - TS2345 - Argument of type 'Element' is not assignable to parameter of type 'HTMLElement'.
              errorState,
              errorCode,
              ERROR_ATTRIBUTE_PREFIX.LOGIN,
              defaultErrorCopy2
            );
          }
        });
      });
    });
  }
  function asyncLogInUser(email, password) {
    return userSystemsRequestClient.mutate({
      mutation: loginMutation,
      variables: {
        email,
        authPassword: password
      }
    });
  }
  var loginFormQuerySelector, errorState, defaultErrorCopy2, errorMsgNode, getLogInErrorCode;
  var init_login = __esm({
    "packages/systems/users/siteBundles/login.ts"() {
      "use strict";
      init_utils3();
      init_constants();
      init_mutations();
      loginFormQuerySelector = `form[${USYS_DATA_ATTRS.formType}="${USYS_FORM_TYPES.login}"]`;
      errorState = document.querySelector(`[${USYS_DATA_ATTRS.formError}]`);
      defaultErrorCopy2 = // @ts-expect-error - TS2532 - Object is possibly 'undefined'.
      logInErrorStates[LOGIN_UI_ERROR_CODES.GENERAL_ERROR].copy;
      errorMsgNode = document.querySelector(`.${ERROR_MSG_CLASS}`);
      getLogInErrorCode = (error) => {
        let errorCode;
        switch (error) {
          case "UsysInvalidCredentials":
            errorCode = LOGIN_UI_ERROR_CODES.INVALID_EMAIL_OR_PASSWORD;
            break;
          default:
            errorCode = LOGIN_UI_ERROR_CODES.GENERAL_ERROR;
        }
        return errorCode;
      };
    }
  });

// packages/systems/users/siteBundles/signup.ts
  var signup_exports = {};
  __export(signup_exports, {
    asyncSignUpUser: () => asyncSignUpUser,
    handleSignUpForms: () => handleSignUpForms
  });
  function getSignupForms() {
    const signupForms = document.querySelectorAll(signupFormQuerySelector);
    return Array.prototype.slice.call(signupForms).filter((signupForm) => signupForm instanceof HTMLFormElement);
  }
  function handleUserInvite(email) {
    const form = document.querySelector(signupFormQuerySelector);
    if (!(form instanceof HTMLFormElement)) {
      return;
    }
    const emailInput = form.querySelector(
      `input[${USYS_DATA_ATTRS.inputType}="${USYS_INPUT_TYPES.email}"]`
    );
    if (!(emailInput instanceof HTMLInputElement)) {
      return;
    }
    emailInput.disabled = true;
    emailInput.classList.add("w-input-disabled");
    emailInput.value = email;
  }
  function handleEmailVerifcation(token, errorState4) {
    const form = document.querySelector(signupFormQuerySelector);
    hideElement(form);
    asyncVerifyEmailToken(token).then(() => {
      const successMessage = document.querySelector(
        `.${USYS_DOM_CLASS_NAMES.formSuccess}`
      );
      const redirectAnchor = document.querySelector(
        `[${USYS_DATA_ATTRS.redirectUrl}] a`
      );
      const redirectPath = getRedirectPath();
      if (redirectPath && redirectAnchor) {
        redirectAnchor.setAttribute("href", encodeURIComponent(redirectPath));
      }
      showElement(successMessage);
      handleRedirect(redirectAnchor?.getAttribute("href") ?? "/", true);
    }).catch((error) => {
      showElement(verificationMessage);
      userFormError(form, errorState4, "SIGNUP")(error);
    });
  }
  function handleSignUpForms() {
    const params = new URLSearchParams(window.location.search);
    const inviteToken = params.get("inviteToken") || "";
    const verifyToken = params.get("verifyToken") || "";
    const errorState4 = document.querySelector(`[${USYS_DATA_ATTRS.formError}]`);
    let turnstileScript = null;
    getSignupForms().forEach((signupForm) => {
      const submitButton = signupForm.querySelector('input[type="submit"]');
      const sendSubmitData = (captchaToken) => {
        const submitText = disableSubmit(submitButton);
        const commonFields = (0, import_fields.getCommonFields)(signupForm);
        const customFields = (0, import_fields.getCustomFields)(signupForm);
        hideElement(errorState4);
        asyncSignUpUser(
          (0, import_fields.getFieldValueById)("email", commonFields) || "",
          (0, import_fields.getFieldValueById)("name", commonFields) || "",
          (0, import_fields.getFieldValueById)("password", commonFields) || "",
          (0, import_fields.getFieldValueById)("accept-privacy", commonFields) || false,
          (0, import_fields.getFieldValueById)("accept-communications", commonFields) || false,
          customFields,
          inviteToken,
          captchaToken
        ).then(() => {
          if (inviteToken) {
            window.location = "/log-in";
          } else {
            hideElement(signupForm);
            showAndFocusElement(verificationMessage);
          }
        }).catch(userFormError(signupForm, errorState4, "SIGNUP")).finally(() => {
          resetSubmit(submitButton, submitText);
        });
      };
      const captchaSiteKey = signupForm.getAttribute("wf-captcha-site-key");
      const captchaMode = signupForm.getAttribute("wf-captcha-mode");
      if (captchaSiteKey && captchaMode && !turnstileScript) {
        submitButton.setAttribute("disabled", "true");
        turnstileScript = document.createElement("script");
        turnstileScript.src = "https://challenges.cloudflare.com/turnstile/v0/api.js";
        document.head.appendChild(turnstileScript);
        turnstileScript.onload = () => {
          signupForm.addEventListener("submit", (e) => {
            e.preventDefault();
            renderTurnstileCaptcha(captchaSiteKey, captchaMode, sendSubmitData);
          });
          submitButton.removeAttribute("disabled");
        };
      } else {
        signupForm.addEventListener("submit", (e) => {
          e.preventDefault();
          sendSubmitData(null);
        });
      }
      if (inviteToken) {
        const email = params.get("email") || "";
        handleUserInvite(email);
      }
      if (verifyToken) {
        handleEmailVerifcation(verifyToken, errorState4);
      }
    });
  }
  function asyncSignUpUser(email, name = "", password, acceptPrivacy, acceptCommunications, customFields, inviteToken, captchaToken) {
    const variables = {
      email,
      name,
      acceptPrivacy,
      acceptCommunications,
      authPassword: password,
      data: (0, import_fields.getFieldsAsTypeKeys)(customFields),
      inviteToken: inviteToken || void 0,
      captchaToken: captchaToken || void 0,
      redirectPath: getRedirectPath()
    };
    return userSystemsRequestClient.mutate({
      mutation: signupMutation,
      variables
    });
  }
  function asyncVerifyEmailToken(verifyToken) {
    return userSystemsRequestClient.mutate({
      mutation: verifyEmailMutation,
      variables: {
        verifyToken,
        redirectPath: getRedirectPath()
      }
    });
  }
  var import_fields, signupFormQuerySelector, verificationMessage;
  var init_signup = __esm({
    "packages/systems/users/siteBundles/signup.ts"() {
      "use strict";
      init_utils3();
      init_constants();
      init_mutations();
      import_fields = __toESM(require_fields());
      init_turnstileCaptcha();
      signupFormQuerySelector = `form[${USYS_DATA_ATTRS.formType}="${USYS_FORM_TYPES.signup}"]`;
      verificationMessage = document.querySelector(
        `.${USYS_DOM_CLASS_NAMES.formVerfication}`
      );
    }
  });

  // packages/systems/users/siteBundles/logout.ts
  var logout_exports = {};
  __export(logout_exports, {
    asyncLogOutUser: () => asyncLogOutUser,
    handleLogInLogOutButton: () => handleLogInLogOutButton
  });
  function getLogoutButtons() {
    const logoutButtons = document.querySelectorAll(logoutButtonQuerySelector);
    return Array.prototype.slice.call(logoutButtons).filter((logoutButton) => logoutButton instanceof HTMLButtonElement);
  }
  function handleGoToLoginClick() {
    if (window.Webflow.env("preview")) {
      return;
    }
    window.location = "/log-in";
  }
  function handleLogOutButtonClick(event) {
    event.preventDefault();
    asyncLogOutUser().then(() => {
      window.Webflow.location("/");
    });
  }
  function handleLogInLogOutButton() {
    getLogoutButtons().forEach((logoutButton) => {
      if (document.cookie.split(";").some((cookie) => cookie.indexOf(LOGGEDIN_COOKIE_NAME) > -1)) {
        logoutButton.innerHTML = logoutButton.getAttribute(USYS_DATA_ATTRS.logout) || "Log out";
        logoutButton.removeEventListener("click", handleGoToLoginClick);
        logoutButton.addEventListener("click", handleLogOutButtonClick);
      } else if (!window.Webflow.env("design")) {
        logoutButton.innerHTML = logoutButton.getAttribute(USYS_DATA_ATTRS.login) || "Log in";
        logoutButton.removeEventListener("click", handleLogOutButtonClick);
        logoutButton.addEventListener("click", handleGoToLoginClick);
      }
    });
  }
  function asyncLogOutUser() {
    return userSystemsRequestClient.mutate({
      mutation: logoutMutation
    });
  }
  var logoutButtonQuerySelector;
  var init_logout = __esm({
    "packages/systems/users/siteBundles/logout.ts"() {
      "use strict";
      init_utils3();
      init_constants();
      init_mutations();
      logoutButtonQuerySelector = `[${USYS_DATA_ATTRS.logout}]`;
    }
  });

  // packages/systems/users/siteBundles/resetPassword.ts
  var resetPassword_exports = {};
  __export(resetPassword_exports, {
    asyncRequestResetPassword: () => asyncRequestResetPassword,
    handleResetPasswordForms: () => handleResetPasswordForms
  });
  function getResetPasswordForms() {
    const resetPasswordForms = document.querySelectorAll(
      resetPasswordFormQuerySelector
    );
    return Array.prototype.slice.call(resetPasswordForms).filter(
      (resetPasswordForm) => resetPasswordForm instanceof HTMLFormElement
    );
  }
  function handleResetPasswordForms() {
    getResetPasswordForms().forEach((resetPasswordForm) => {
      resetPasswordForm.addEventListener("submit", (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const successMessage = document.querySelector(
          `.${USYS_DOM_CLASS_NAMES.formSuccess}`
        );
        if (!(form instanceof HTMLFormElement)) {
          return;
        }
        hideElement(errorState2);
        const emailInput = form.querySelector(
          `input[${USYS_DATA_ATTRS.inputType}="${USYS_INPUT_TYPES.email}"]`
        );
        if (!(emailInput instanceof HTMLInputElement)) {
          return;
        }
        asyncRequestResetPassword(emailInput.value).then(() => {
          hideElement(form);
          showAndFocusElement(successMessage);
        }).catch((error) => {
          if (errorState2) {
            const elementErrorCode = error?.graphQLErrors?.[0]?.code ?? "";
            const errorCode = getResetPasswordErrorCode(elementErrorCode);
            handleErrorNode(
              errorMsgNode2,
              // @ts-expect-error - TS2345 - Argument of type 'Element' is not assignable to parameter of type 'HTMLElement'.
              errorState2,
              errorCode,
              ERROR_ATTRIBUTE_PREFIX.RESET_PASSWORD,
              defaultErrorCopy3
            );
          }
        });
      });
    });
  }
  function asyncRequestResetPassword(email) {
    return userSystemsRequestClient.mutate({
      mutation: resetPasswordMutation,
      variables: {
        email
      }
    });
  }
  var resetPasswordFormQuerySelector, errorState2, defaultErrorCopy3, errorMsgNode2, getResetPasswordErrorCode;
  var init_resetPassword = __esm({
    "packages/systems/users/siteBundles/resetPassword.ts"() {
      "use strict";
      init_utils3();
      init_constants();
      init_mutations();
      resetPasswordFormQuerySelector = `form[${USYS_DATA_ATTRS.formType}="${USYS_FORM_TYPES.resetPassword}"]`;
      errorState2 = document.querySelector(`[${USYS_DATA_ATTRS.formError}]`);
      defaultErrorCopy3 = // @ts-expect-error - TS2532 - Object is possibly 'undefined'.
      resetPasswordErrorStates[RESET_PASSWORD_UI_ERROR_CODES.GENERAL_ERROR].copy;
      errorMsgNode2 = document.querySelector(`.${ERROR_MSG_CLASS}`);
      getResetPasswordErrorCode = (error) => {
        let errorCode;
        switch (error) {
          default:
            errorCode = RESET_PASSWORD_UI_ERROR_CODES.GENERAL_ERROR;
        }
        return errorCode;
      };
    }
  });