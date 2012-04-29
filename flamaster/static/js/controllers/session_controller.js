// Generated by CoffeeScript 1.3.1
var __bind = function(fn, me){ return function(){ return fn.apply(me, arguments); }; },
  __hasProp = {}.hasOwnProperty,
  __extends = function(child, parent) { for (var key in parent) { if (__hasProp.call(parent, key)) child[key] = parent[key]; } function ctor() { this.constructor = child; } ctor.prototype = parent.prototype; child.prototype = new ctor; child.__super__ = parent.prototype; return child; };

define(['chaplin/mediator', 'chaplin/lib/utils', 'chaplin/controller', 'chaplin/lib/services/custom', 'models/user', 'views/login_view'], function(mediator, utils, Controller, Custom, User, LoginView) {
  'use strict';

  var SessionController;
  return SessionController = (function(_super) {

    __extends(SessionController, _super);

    SessionController.name = 'SessionController';

    function SessionController() {
      this.logout = __bind(this.logout, this);

      this.serviceProviderSession = __bind(this.serviceProviderSession, this);

      this.loginAttempt = __bind(this.loginAttempt, this);

      this.triggerLogin = __bind(this.triggerLogin, this);
      return SessionController.__super__.constructor.apply(this, arguments);
    }

    SessionController.serviceProviders = {
      custom: new Custom
    };

    SessionController.prototype.loginStatusDetermined = false;

    SessionController.prototype.loginView = null;

    SessionController.prototype.serviceProviderName = null;

    SessionController.prototype.initialize = function() {
      console.debug('SessionController#initialize');
      this.subscribeEvent('loginAttempt', this.loginAttempt);
      this.subscribeEvent('serviceProviderSession', this.serviceProviderSession);
      this.subscribeEvent('logout', this.logout);
      this.subscribeEvent('userData', this.userData);
      this.subscribeEvent('!showLogin', this.showLoginView);
      this.subscribeEvent('!login', this.triggerLogin);
      this.subscribeEvent('!logout', this.triggerLogout);
      return this.getSession();
    };

    SessionController.prototype.loadSDKs = function() {
      var name, serviceProvider, _ref, _results;
      _ref = SessionController.serviceProviders;
      _results = [];
      for (name in _ref) {
        serviceProvider = _ref[name];
        _results.push(serviceProvider.loadSDK());
      }
      return _results;
    };

    SessionController.prototype.createUser = function(userData) {
      var user;
      user = new User(userData);
      return mediator.user = user;
    };

    SessionController.prototype.getSession = function() {
      var name, serviceProvider, _ref, _results;
      this.loadSDKs();
      _ref = SessionController.serviceProviders;
      _results = [];
      for (name in _ref) {
        serviceProvider = _ref[name];
        _results.push(serviceProvider.done(serviceProvider.getLoginStatus));
      }
      return _results;
    };

    SessionController.prototype.showLoginView = function() {
      if (this.loginView) {
        return;
      }
      this.loadSDKs();
      return this.loginView = new LoginView({
        serviceProviders: SessionController.serviceProviders
      });
    };

    SessionController.prototype.hideLoginView = function() {
      if (!this.loginView) {
        return;
      }
      this.loginView.dispose();
      return this.loginView = null;
    };

    SessionController.prototype.triggerLogin = function(serviceProviderName, loginData) {
      var serviceProvider;
      serviceProvider = SessionController.serviceProviders[serviceProviderName];
      if (!serviceProvider.isLoaded()) {
        mediator.publish('serviceProviderMissing', serviceProviderName);
        return;
      }
      mediator.publish('loginAttempt', serviceProviderName);
      return serviceProvider.triggerLogin(loginData);
    };

    SessionController.prototype.loginAttempt = function() {
      return console.debug('SessionController#loginAttempt');
    };

    SessionController.prototype.serviceProviderSession = function(session) {
      this.serviceProviderName = session.provider.name;
      console.debug('SessionController#serviceProviderSession', session, this.serviceProviderName);
      this.hideLoginView();
      session.id = session.userId;
      delete session.userId;
      this.createUser(session);
      return this.publishLogin();
    };

    SessionController.prototype.publishLogin = function() {
      this.loginStatusDetermined = true;
      mediator.publish('login', mediator.user);
      return mediator.publish('loginStatus', true);
    };

    SessionController.prototype.triggerLogout = function() {
      return mediator.publish('logout');
    };

    SessionController.prototype.logout = function() {
      this.loginStatusDetermined = true;
      if (mediator.user) {
        mediator.user.dispose();
        mediator.user = null;
      }
      this.serviceProviderName = null;
      this.showLoginView();
      return mediator.publish('loginStatus', false);
    };

    SessionController.prototype.userData = function(data) {
      return mediator.user.set(data);
    };

    return SessionController;

  })(Controller);
});
