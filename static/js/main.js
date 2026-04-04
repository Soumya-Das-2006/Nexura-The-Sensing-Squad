/*!
 * nexura.js — Main JavaScript for Nexura
 * Guidewire DEVTrails 2026
 */
(function ($) {
  "use strict";

  /* ── Spinner ─────────────────────────────────────────────────── */
  var spinner = function () {
    setTimeout(function () {
      if ($('#spinner').length > 0) {
        $('#spinner').removeClass('show');
      }
    }, 1);
  };
  spinner();

  /* ── Sticky Navbar ───────────────────────────────────────────── */
  $(window).scroll(function () {
    if ($(this).scrollTop() > 45) {
      $('.nav-bar').addClass('sticky-top shadow-sm');
    } else {
      $('.nav-bar').removeClass('sticky-top shadow-sm');
    }
  });

  /* ── Back to Top ─────────────────────────────────────────────── */
  $(window).scroll(function () {
    if ($(this).scrollTop() > 300) {
      $('.back-to-top').fadeIn('slow');
    } else {
      $('.back-to-top').fadeOut('slow');
    }
  });
  $('.back-to-top').click(function () {
    $('html, body').animate({ scrollTop: 0 }, 1500, 'easeInOutExpo');
    return false;
  });

  /* ── Facts Counter ───────────────────────────────────────────── */
  $('[data-toggle="counter-up"]').counterUp({ delay: 10, time: 2000 });

  /* ── Hero Carousel ───────────────────────────────────────────── */
  $(".header-carousel").owlCarousel({
    autoplay: true,
    smartSpeed: 1500,
    items: 1,
    dots: true,
    loop: true,
    nav: true,
    navText: [
      '<i class="fa fa-angle-left"></i>',
      '<i class="fa fa-angle-right"></i>'
    ]
  });

  /* ── Testimonial Carousel ────────────────────────────────────── */
  $(".testimonial-carousel").owlCarousel({
    autoplay: true,
    smartSpeed: 1000,
    margin: 24,
    dots: false,
    loop: true,
    nav: true,
    navText: [
      '<i class="fa fa-angle-left me-2"></i>Prev',
      'Next<i class="fa fa-angle-right ms-2"></i>'
    ],
    responsive: {
      0:   { items: 1 },
      768: { items: 2 }
    }
  });

  /* ── WOW Animations ──────────────────────────────────────────── */
  new WOW().init();

  /* ── Lightbox ────────────────────────────────────────────────── */
  if (typeof lightbox !== 'undefined') {
    lightbox.option({
      resizeDuration: 200,
      wrapAround: true
    });
  }

  /* ── Sidebar toggle (mobile dashboard) ──────────────────────── */
  $('#sidebarToggle').on('click', function () {
    $('.nexura-sidebar').toggleClass('open');
    $('body').toggleClass('sidebar-open');
  });
  // Close sidebar when clicking outside on mobile
  $(document).on('click', function (e) {
    if ($(window).width() < 992) {
      if (!$(e.target).closest('.nexura-sidebar, #sidebarToggle').length) {
        $('.nexura-sidebar').removeClass('open');
        $('body').removeClass('sidebar-open');
      }
    }
  });

  /* ── OTP inputs: auto-advance and paste ─────────────────────── */
  var $otpInputs = $('.otp-inputs input, .otp-digit');
  if ($otpInputs.length) {
    $otpInputs.on('input', function () {
      var $this = $(this);
      var val   = $this.val().replace(/\D/g, '').slice(0, 1);
      $this.val(val);
      if (val) {
        $this.next('input, .otp-digit').focus();
      }
    });
    $otpInputs.on('keydown', function (e) {
      if (e.key === 'Backspace' && !$(this).val()) {
        $(this).prev('input, .otp-digit').focus();
      }
    });
    $otpInputs.on('paste', function (e) {
      e.preventDefault();
      var paste = (e.originalEvent.clipboardData || window.clipboardData)
                    .getData('text').replace(/\D/g, '');
      $otpInputs.each(function (i) {
        $(this).val(paste[i] || '');
      });
      $otpInputs.last().focus();
    });
  }

  /* ── OTP countdown timer ─────────────────────────────────────── */
  if ($('#otpCountdown').length) {
    var seconds = parseInt($('#otpCountdown').data('seconds') || 30);
    var timer = setInterval(function () {
      seconds--;
      if (seconds <= 0) {
        clearInterval(timer);
        $('#otpCountdown').html(
          '<a href="#" id="resendOtpBtn" class="text-primary fw-semibold">Resend OTP</a>'
        );
      } else {
        $('#otpCountdown').text('Resend in ' + seconds + 's');
      }
    }, 1000);
  }

  /* ── Plan card selection ─────────────────────────────────────── */
  $('.plan-card').on('click', function () {
    $('.plan-card').removeClass('selected');
    $(this).addClass('selected');
    var slug = $(this).data('plan');
    if (slug) {
      $('#selectedPlan').val(slug);
    }
  });

  /* ── Auto-dismiss flash messages ────────────────────────────── */
  setTimeout(function () {
    $('.nexura-alert[data-auto-dismiss]').fadeOut(600);
  }, 4000);

  /* ── Confirm dialogs ─────────────────────────────────────────── */
  $('[data-confirm]').on('click', function (e) {
    var msg = $(this).data('confirm') || 'Are you sure?';
    if (!confirm(msg)) {
      e.preventDefault();
    }
  });

  /* ── Copy UTR to clipboard ───────────────────────────────────── */
  $(document).on('click', '.utr-ref', function () {
    var text = $(this).text().trim();
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(function () {
        nexuraToast('UTR copied to clipboard!', 'success');
      });
    }
  });

  /* ── Toast helper ────────────────────────────────────────────── */
  window.nexuraToast = function (message, type) {
    type = type || 'info';
    var colors = {
      success: '#dcfce7,#166534',
      danger:  '#fee2e2,#991b1b',
      warning: '#fef3c7,#92400e',
      info:    '#dbeafe,#1e40af'
    };
    var pair = (colors[type] || colors.info).split(',');
    var $toast = $(
      '<div style="position:fixed;bottom:24px;left:50%;transform:translateX(-50%);\
       padding:10px 20px;border-radius:8px;font-size:14px;font-weight:600;\
       z-index:9999;box-shadow:0 4px 14px rgba(0,0,0,.15);white-space:nowrap;\
       background:' + pair[0] + ';color:' + pair[1] + ';">' + message + '</div>'
    );
    $('body').append($toast);
    setTimeout(function () { $toast.fadeOut(400, function () { $toast.remove(); }); }, 2500);
  };

})(jQuery);
