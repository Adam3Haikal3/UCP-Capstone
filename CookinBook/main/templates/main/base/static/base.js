$(document).ready(function() {
    if ($(window).width() < 992) {
        $('#navbarNavDropdown').removeClass('show');
    }

    var $navbar = $('#navbar');

    function checkScroll() {
        if (window.scrollY > 50) {
            $navbar.addClass('navbar-scrolled');
        } else {
            $navbar.removeClass('navbar-scrolled');
        }
    }

    $(window).on('scroll', checkScroll);
    checkScroll();
});